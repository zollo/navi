"""Custom domains: claim a hostname for your page, prove it with DNS, serve it.

Flow: the owner sets a hostname, adds two DNS records (a TXT record with a token,
and a CNAME/A record pointing at Navi), then verifies. A verified hostname is
returned by `lookup` (used by the SPA and as the TLS "may I issue a certificate"
check) and gets an Ingress + certificate from the domain sync job
(`app.domain_sync`). Verified domains are re-checked periodically and switched off
when their records stay gone, so a lapsed domain can't keep pointing at a page.
"""
from __future__ import annotations

import ipaddress
import re
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import dns.asyncresolver
import dns.exception
import dns.resolver
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import Conflict, Forbidden, Invalid, NotFound
from app.models.domain import CustomDomain
from app.models.page import Page
from app.models.user import User
from app.schemas.domain import DnsRecord, DomainConfig, DomainIn, DomainLookup, DomainRead

# TXT record name prefix and value prefix for the ownership check.
CHALLENGE_LABEL = "_navi-challenge"
TOKEN_PREFIX = "navi-verify="

# Pending domains are checked automatically for a week, every few minutes.
PENDING_RECHECK = timedelta(minutes=5)
PENDING_WINDOW = timedelta(days=7)
# Verified domains are re-checked a few times a day and switched off after this
# many failures in a row (about a day), so a short DNS outage doesn't take them down.
ACTIVE_RECHECK = timedelta(hours=6)
MAX_FAILURES = 4

_LABEL_RE = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")

DISABLED = "Custom domains aren't enabled on this server"
IN_USE = "This domain is already connected to another page"


class DnsError(Exception):
    """A lookup failed for a reason other than "no such record" (timeout, SERVFAIL)."""


class PublicDns:
    """Resolves through public resolvers (settings.custom_domain_resolvers), so the
    answer matches what browsers and Let's Encrypt see, not split-horizon DNS."""

    def _resolver(self) -> dns.asyncresolver.Resolver:
        servers = settings.custom_domain_resolver_list
        resolver = dns.asyncresolver.Resolver(configure=not servers)
        if servers:
            resolver.nameservers = servers
        resolver.lifetime = 5.0
        return resolver

    async def _query(self, name: str, rdtype: str):
        try:
            return await self._resolver().resolve(name, rdtype, search=False)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return None
        except dns.exception.DNSException as exc:
            raise DnsError(f"DNS lookup for {name} failed ({exc.__class__.__name__})") from exc

    async def txt(self, name: str) -> list[str]:
        answer = await self._query(name, "TXT")
        if answer is None:
            return []
        return [b"".join(r.strings).decode("utf-8", "replace") for r in answer]

    async def addresses(self, name: str) -> set[str]:
        """IPv4 addresses, following CNAMEs."""
        answer = await self._query(name, "A")
        return set() if answer is None else {r.address for r in answer}


# Swapped out in tests.
dns_client = PublicDns()


def _now() -> datetime:
    return datetime.now(UTC)


def config() -> DomainConfig:
    return DomainConfig(
        enabled=settings.custom_domains_enabled,
        cname_target=settings.custom_domain_cname_target,
        ips=settings.custom_domain_ip_list,
    )


def normalize_hostname(value: str) -> str:
    """Lowercase ASCII hostname from what someone typed or pasted (URL, trailing dot,
    unicode). Raises Invalid when it isn't a usable public hostname."""
    v = value.strip().lower()
    v = (urlsplit(v).hostname or "") if "://" in v else v.split("/")[0].split(":")[0]
    v = v.rstrip(".")
    try:
        v = v.encode("idna").decode("ascii")
    except UnicodeError:
        raise Invalid("Enter a domain name such as www.example.com") from None
    try:
        ipaddress.ip_address(v)
    except ValueError:
        pass
    else:
        raise Invalid("Use a domain name, not an IP address")
    labels = v.split(".")
    if (
        len(v) > 253
        or len(labels) < 2
        or not all(_LABEL_RE.match(label) for label in labels)
        or labels[-1].isdigit()
    ):
        raise Invalid("Enter a domain name such as www.example.com")
    for blocked in settings.custom_domain_blocked_list:
        if v == blocked or v.endswith("." + blocked):
            raise Invalid(f"Domains under {blocked} can't be used")
    return v


def is_apex(hostname: str) -> bool:
    """Best guess at "can't have a CNAME": a registrable domain like example.com."""
    return hostname.count(".") == 1


def records(domain: CustomDomain) -> list[DnsRecord]:
    out = [
        DnsRecord(
            type="TXT",
            name=f"{CHALLENGE_LABEL}.{domain.hostname}",
            value=f"{TOKEN_PREFIX}{domain.token}",
            purpose="Proves you own the domain. Keep it: it's checked again from time to time.",
        )
    ]
    ips = settings.custom_domain_ip_list
    if is_apex(domain.hostname) and ips:
        out += [
            DnsRecord(type="A", name=domain.hostname, value=ip, purpose="Sends visitors to Navi.")
            for ip in ips
        ]
    else:
        out.append(
            DnsRecord(
                type="CNAME",
                name=domain.hostname,
                value=settings.custom_domain_cname_target,
                purpose="Sends visitors to Navi.",
            )
        )
    return out


def to_read(domain: CustomDomain) -> DomainRead:
    return DomainRead(
        hostname=domain.hostname,
        status="active" if domain.verified else "pending",
        url=f"https://{domain.hostname}",
        records=records(domain),
        verified_at=domain.verified_at,
        last_checked_at=domain.last_checked_at,
        last_error=domain.last_error,
        created_at=domain.created_at,
    )


async def check_dns(hostname: str, token: str) -> str | None:
    """Why `hostname` isn't ready, or None when both records are in place."""
    try:
        txt_name = f"{CHALLENGE_LABEL}.{hostname}"
        if f"{TOKEN_PREFIX}{token}" not in await dns_client.txt(txt_name):
            return f"TXT record {txt_name} not found yet (or its value doesn't match)"
        target = settings.custom_domain_cname_target
        expected = set(settings.custom_domain_ip_list) or await dns_client.addresses(target)
        if not expected:
            return f"Couldn't resolve {target}; ask the server admin to check CUSTOM_DOMAIN_TARGET"
        actual = await dns_client.addresses(hostname)
        if not actual:
            return f"{hostname} doesn't point anywhere yet: add the CNAME (or A) record"
        if not actual <= expected:
            stray = ", ".join(sorted(actual - expected))
            return f"{hostname} points at {stray}, not at {target}"
    except DnsError as exc:
        return str(exc)
    return None


async def _verified_elsewhere(
    db: AsyncSession, hostname: str, domain: CustomDomain | None = None
) -> bool:
    """Whether another page has already verified `hostname`."""
    stmt = select(CustomDomain.id).where(
        CustomDomain.hostname == hostname, CustomDomain.verified_at.is_not(None)
    )
    if domain is not None:
        stmt = stmt.where(CustomDomain.id != domain.id)
    return (await db.execute(stmt)).first() is not None


async def run_check(db: AsyncSession, domain: CustomDomain) -> None:
    """Check DNS and update the domain's state (not committed)."""
    error = await check_dns(domain.hostname, domain.token)
    domain.last_checked_at = _now()
    if (
        error is None
        and not domain.verified
        and await _verified_elsewhere(db, domain.hostname, domain)
    ):
        error = IN_USE
    if error is None:
        domain.last_error = None
        domain.failures = 0
        if not domain.verified:
            domain.verified_at = _now()
        return
    if domain.verified:
        domain.failures += 1
        if domain.failures >= MAX_FAILURES:
            domain.verified_at = None
            domain.failures = 0
            error = f"Switched off after failing checks for a day: {error}"
    domain.last_error = error


async def _page_for(db: AsyncSession, user: User) -> Page:
    result = await db.execute(select(Page).where(Page.user_id == user.id))
    page = result.scalar_one_or_none()
    if page is None:
        raise NotFound("Create your page before adding a domain")
    return page


async def get_mine(db: AsyncSession, user: User) -> DomainRead:
    page = await _page_for(db, user)
    if page.domain is None:
        raise NotFound("You haven't added a custom domain")
    return to_read(page.domain)


async def set_mine(db: AsyncSession, user: User, data: DomainIn) -> tuple[DomainRead, bool]:
    """Claim a hostname for the caller's page, replacing any previous one."""
    if not settings.custom_domains_enabled:
        raise Forbidden(DISABLED)
    page = await _page_for(db, user)
    hostname = normalize_hostname(data.hostname)
    domain = page.domain
    if domain is not None and domain.hostname == hostname:
        return to_read(domain), False
    if await _verified_elsewhere(db, hostname, domain):
        raise Conflict(IN_USE)

    created = domain is None
    if domain is None:
        domain = CustomDomain(page=page)
        db.add(domain)
    domain.hostname = hostname
    domain.token = secrets.token_hex(16)
    domain.verified_at = None
    domain.last_checked_at = None
    domain.last_error = None
    domain.failures = 0
    await db.commit()
    await db.refresh(domain)
    return to_read(domain), created


async def verify_mine(db: AsyncSession, user: User) -> DomainRead:
    """Check the caller's domain now instead of waiting for the next automatic check."""
    if not settings.custom_domains_enabled:
        raise Forbidden(DISABLED)
    page = await _page_for(db, user)
    domain = page.domain
    if domain is None:
        raise NotFound("You haven't added a custom domain")
    await run_check(db, domain)
    try:
        await db.commit()
    except IntegrityError:
        # Another page verified the same hostname at the same moment.
        await db.rollback()
        raise Conflict(IN_USE) from None
    await db.refresh(domain)
    return to_read(domain)


async def delete_mine(db: AsyncSession, user: User) -> None:
    page = await _page_for(db, user)
    if page.domain is None:
        raise NotFound("You haven't added a custom domain")
    page.domain = None
    await db.commit()


async def lookup(db: AsyncSession, hostname: str) -> DomainLookup:
    """The page a verified domain shows; 404 for anything else."""
    if not settings.custom_domains_enabled:
        raise NotFound("Unknown domain")
    try:
        hostname = normalize_hostname(hostname)
    except Invalid:
        raise NotFound("Unknown domain") from None
    result = await db.execute(
        select(CustomDomain.hostname, Page.handle)
        .join(Page, Page.id == CustomDomain.page_id)
        .where(CustomDomain.hostname == hostname, CustomDomain.verified_at.is_not(None))
    )
    row = result.first()
    if row is None:
        raise NotFound("Unknown domain")
    return DomainLookup(
        hostname=row.hostname, handle=row.handle, primary_url=settings.public_url.rstrip("/")
    )


async def recheck_due(db: AsyncSession) -> int:
    """Check pending domains (for a week after they're added) and re-check verified
    ones. Commits after each domain. Returns how many were checked."""
    now = _now()
    due = or_(
        and_(
            CustomDomain.verified_at.is_(None),
            CustomDomain.created_at > now - PENDING_WINDOW,
            or_(
                CustomDomain.last_checked_at.is_(None),
                CustomDomain.last_checked_at < now - PENDING_RECHECK,
            ),
        ),
        and_(
            CustomDomain.verified_at.is_not(None),
            or_(
                CustomDomain.last_checked_at.is_(None),
                CustomDomain.last_checked_at < now - ACTIVE_RECHECK,
            ),
        ),
    )
    result = await db.execute(
        select(CustomDomain.id).where(due).order_by(CustomDomain.created_at)
    )
    checked = 0
    # Load each domain fresh: a rollback expires every object in the session.
    for domain_id in result.scalars().all():
        domain = await db.get(CustomDomain, domain_id)
        if domain is None:
            continue
        await run_check(db, domain)
        try:
            await db.commit()
        except IntegrityError:
            # Another page verified the same hostname first.
            await db.rollback()
        checked += 1
    return checked


async def active_hostnames(db: AsyncSession) -> list[str]:
    if not settings.custom_domains_enabled:
        return []
    result = await db.execute(
        select(CustomDomain.hostname)
        .where(CustomDomain.verified_at.is_not(None))
        .order_by(CustomDomain.hostname)
    )
    return list(result.scalars().all())
