"""Smoke test: the FastAPI app builds and its schema generates."""
from __future__ import annotations


def test_app_and_openapi_build():
    from app.main import app

    assert app.title == "Navi"
    paths = app.openapi()["paths"]
    assert "/api/health" in paths
    assert "/api/pages/{handle}" in paths
    assert "/api/pages/me" in paths
    # Checking a handle works anonymously.
    assert {} in paths["/api/pages/handles/{handle}"]["get"]["security"]


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
