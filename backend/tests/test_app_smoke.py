"""Smoke test: the FastAPI app builds and its schema generates."""
from __future__ import annotations


def test_app_and_openapi_build():
    from app.main import app

    assert app.title == "Navi"
    paths = app.openapi()["paths"]
    assert "201" in paths["/api/pages/me"]["put"]["responses"]
    assert "/api/health" in paths
    assert "/api/pages/{handle}" in paths
    assert "/api/pages/me" in paths
    # Checking a handle works anonymously.
    assert {} in paths["/api/pages/handles/{handle}"]["get"]["security"]


def test_database_url_escapes_credentials():
    from sqlalchemy.engine import make_url

    from app.config import Settings

    s = Settings(DATABASE_URL=None, POSTGRES_PASSWORD="p@ss:w/rd%", POSTGRES_HOST="db")
    url = make_url(s.database_url)
    assert url.password == "p@ss:w/rd%"
    assert url.host == "db"
    assert make_url(s.sync_database_url).drivername == "postgresql+psycopg2"


def test_production_refuses_placeholder_secret():
    import pytest
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(NAVI_ENV="production", SECRET_KEY="change-me")
    assert Settings(NAVI_ENV="production", SECRET_KEY="x" * 64).env == "production"


def test_reserved_handles_cover_spa_routes():
    """Every top-level SPA/nginx path must be reserved, or a page could shadow it."""
    from app.services.page_service import RESERVED_HANDLES

    for route in ("login", "register", "edit", "account", "api", "docs", "redoc", "assets"):
        assert route in RESERVED_HANDLES
    # Fixed routes under /api/pages/ that a handle would collide with.
    for route in ("me", "icons", "handles"):
        assert route in RESERVED_HANDLES
    # Files the SPA serves at the top level (frontend/public).
    for route in ("favicon.ico", "apple-touch-icon.png", "site.webmanifest"):
        assert route in RESERVED_HANDLES
