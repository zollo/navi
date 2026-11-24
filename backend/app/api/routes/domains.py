"""Custom domains: point your own domain (e.g. www.example.com) at your page."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.domain import DomainConfig, DomainIn, DomainLookup, DomainRead
from app.services import domain_service

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("/config", response_model=DomainConfig, operation_id="get_domain_config")
async def get_domain_config() -> DomainConfig:
    """Whether custom domains are offered, and the CNAME/A targets to point them at."""
    return domain_service.config()


@router.get("/lookup", response_model=DomainLookup, operation_id="lookup_domain")
async def lookup_domain(
    domain: str = Query(min_length=1, max_length=300),
    db: AsyncSession = Depends(get_db),
) -> DomainLookup:
    """The page a verified custom domain shows, or 404.

    The SPA calls this to find out which page to render on a custom domain. It also
    works as an on-demand TLS "ask" endpoint (e.g. Caddy): 200 means the domain is
    allowed a certificate.
    """
    return await domain_service.lookup(db, domain)


@router.get("/me", response_model=DomainRead, operation_id="get_my_domain")
async def get_my_domain(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DomainRead:
    """Your page's custom domain and the DNS records it needs, or 404 if none."""
    return await domain_service.get_mine(db, user)


@router.put(
    "/me",
    response_model=DomainRead,
    operation_id="set_my_domain",
    responses={201: {"model": DomainRead, "description": "Domain added"}},
)
async def set_my_domain(
    payload: DomainIn,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DomainRead:
    """Connect a domain to your page, replacing any previous one.

    The domain starts out pending: add the returned DNS records, then verify. It's
    checked automatically every few minutes for a week, too.
    """
    domain, created = await domain_service.set_mine(db, user, payload)
    if created:
        response.status_code = status.HTTP_201_CREATED
    return domain


@router.post("/me/verify", response_model=DomainRead, operation_id="verify_my_domain")
async def verify_my_domain(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DomainRead:
    """Check your domain's DNS records now."""
    return await domain_service.verify_mine(db, user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_my_domain")
async def delete_my_domain(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Disconnect your custom domain. Your page stays at /<handle>."""
    await domain_service.delete_mine(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
