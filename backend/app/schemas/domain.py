"""Custom domain schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DomainConfig(BaseModel):
    """Whether this server offers custom domains, and where to point them."""

    enabled: bool
    # CNAME target for subdomains such as www.example.com.
    cname_target: str
    # A-record addresses for apex domains such as example.com (may be empty).
    ips: list[str]


class DomainIn(BaseModel):
    # A hostname such as www.example.com; a pasted URL is accepted too.
    hostname: str = Field(min_length=1, max_length=300)


class DnsRecord(BaseModel):
    """A record the owner adds at their DNS provider."""

    type: Literal["TXT", "CNAME", "A"]
    name: str
    value: str
    purpose: str


class DomainRead(BaseModel):
    hostname: str
    # pending: waiting for DNS; active: verified and served.
    status: Literal["pending", "active"]
    url: str
    records: list[DnsRecord]
    verified_at: datetime | None
    last_checked_at: datetime | None
    # Why the last check failed; null after a passing check or before the first.
    last_error: str | None
    created_at: datetime


class DomainLookup(BaseModel):
    """Which page a verified custom domain shows."""

    hostname: str
    handle: str
    # Navi's own address, for "create your own page" links.
    primary_url: str
