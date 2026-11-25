"""Aggregate API router, mounted at /api."""
from fastapi import APIRouter

from app.api.routes import auth, backgrounds, health, imports, pages

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(pages.router)
api_router.include_router(backgrounds.router)
api_router.include_router(imports.router)
