"""Navi FastAPI application: REST API at /api."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.config import settings
from app.core.errors import NaviError

logging.basicConfig(level=logging.INFO)

DESCRIPTION = """\
Navi gives everyone one simple page for their important links, public at
`/<handle>`.

* Read any page anonymously with `GET /api/pages/{handle}`.
* Sign up or sign in with `POST /api/auth/register` / `POST /api/auth/login`, then send
  `Authorization: Bearer <token>` to create and edit your own page at `/api/pages/me`.
"""

app = FastAPI(title="Navi", description=DESCRIPTION, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NaviError)
async def _navi_error(_: Request, exc: NaviError) -> JSONResponse:
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"name": "Navi", "version": app.version, "docs": "/docs"}
