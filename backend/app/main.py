"""Navi FastAPI application: REST API at /api, MCP server at /mcp."""
from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.routing import Route

from app.api.routes import api_router
from app.config import settings
from app.core.errors import NaviError
from app.mcp_server import MCP_PATH, NaviMCP

logging.basicConfig(level=logging.INFO)


class _RedactKeys(logging.Filter):
    """Keep API keys passed as ?key= (URL-only MCP clients) out of access logs."""

    _pattern = re.compile(r"([?&]key=)[^&\s]*")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                self._pattern.sub(r"\1[redacted]", a) if isinstance(a, str) else a
                for a in record.args
            )
        elif isinstance(record.msg, str):
            record.msg = self._pattern.sub(r"\1[redacted]", record.msg)
        return True


logging.getLogger("uvicorn.access").addFilter(_RedactKeys())

DESCRIPTION = """\
Navi gives everyone one simple page for their important links, public at
`/<handle>`.

* Read any page anonymously with `GET /api/pages/{handle}`.
* Sign up or sign in with `POST /api/auth/register` / `POST /api/auth/login`, then send
  `Authorization: Bearer <token>` to create and edit your own page at `/api/pages/me`.
* For scripts and AI tools, create a personal API key (`navi_…`) in the app under
  Account → AI tools and send it the same way.
* The same operations are **MCP tools** over streamable HTTP at `/mcp`, generated from
  this schema: each tool is named after the `operationId` of its REST counterpart.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with mcp.lifespan():
        yield


app = FastAPI(
    title="Navi", description=DESCRIPTION, version=settings.app_version, lifespan=lifespan
)
mcp = NaviMCP(app)

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
for _path in (MCP_PATH, MCP_PATH + "/"):
    app.router.routes.append(Route(_path, endpoint=mcp, methods=["GET", "POST", "DELETE"]))


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"name": "Navi", "version": app.version, "docs": "/docs", "mcp": MCP_PATH}
