"""MCP server, served over streamable HTTP at /mcp.

The tools are generated from the REST API's own OpenAPI schema when the app starts:
every operation becomes a tool named after its `operationId`, with an input schema
built from its path/query parameters and request body, and a call to a tool runs the
real REST route in-process (same validation, permissions and errors). Adding or
changing a route changes the MCP server with no extra code. Operations that make
no sense for an AI client are listed in `EXCLUDED` with the reason;
`tests/test_mcp.py` fails if an entry there goes stale, and CI fails if
`docs/mcp-tools.json` (the published tool list) differs from what the code serves.

Auth: `Authorization: Bearer <API key>` (a session token works too), or `?key=<API
key>` on the URL for clients that only take a URL. The transport is stateless (JSON
responses, no session affinity), so any number of backend replicas can serve it.
"""
from __future__ import annotations

import base64
import binascii
import contextlib
import copy
import json
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, quote

import httpx2
import mcp_types as types
from fastapi import FastAPI
from mcp.server.lowlevel import Server
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from app.config import settings
from app.db import AsyncSessionLocal
from app.models.user import User
from app.services import user_service

SERVER_NAME = "navi"
MCP_PATH = "/mcp"

INSTRUCTIONS = """\
Navi gives every user one simple public page for their important links, at
<public URL>/<handle>: avatar, title, tagline, a row of social icons, and link cards
grouped under section headings. These tools act as the user who owns the API key.

* get_my_page reads the user's page (404 until they have created one).
* save_my_page creates or REPLACES the whole page: send every section and link you
  want to keep, in display order. Read the page first and change only what was asked.
* list_icons gives the icon names accepted for social icons and links; check_handle
  tells whether a handle is free. URLs must start with https://, http:// or mailto:.
* Themes (colors, fonts, buttons, backgrounds) live in the page's `theme`;
  list_backgrounds shows the curated gallery.
* Uploads (avatar, background image) take the image as base64.
"""

# Operations that are not exposed as tools, and why. Everything else is.
EXCLUDED: dict[str, str] = {
    "health": "Infrastructure probe.",
    "readiness": "Infrastructure probe.",
    "login": "MCP clients authenticate with an API key.",
    "register": "MCP clients authenticate with an API key.",
    "auth_config": "Only tells the sign-in page what to render.",
    "update_me": "Changing the password needs a password sign-in, not an API key.",
    "list_api_keys": "API keys can't manage API keys.",
    "create_api_key": "API keys can't manage API keys.",
    "revoke_api_key": "API keys can't manage API keys.",
    "get_avatar": "Returns image bytes; page data carries the avatar URL.",
    "get_page_background": "Returns image bytes; page data carries the image URL.",
    "get_background_image": "Returns image bytes; the gallery carries the image URLs.",
    "lookup_domain": "Used by the SPA and the TLS issuer on custom domains.",
}

_REF_PREFIX = "#/components/schemas/"
_DEFS_PREFIX = "#/$defs/"
_IMAGE_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


@dataclass
class Operation:
    """One REST operation and the tool generated from it."""

    tool: types.Tool
    method: str
    path: str
    admin_only: bool
    path_params: list[str] = field(default_factory=list)
    query_params: list[str] = field(default_factory=list)
    # "json" or "multipart" when the operation takes a body.
    body_kind: str | None = None
    # Body fields taken from top-level arguments; None means the whole body is `body`.
    body_fields: list[str] | None = None
    # Multipart fields carrying a file (sent base64 as an argument of the same name).
    file_fields: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- schema


def _walk_refs(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(_REF_PREFIX):
            yield ref[len(_REF_PREFIX) :]
        for value in node.values():
            yield from _walk_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_refs(value)


def _rewrite_refs(node: Any) -> Any:
    if isinstance(node, dict):
        out = {k: _rewrite_refs(v) for k, v in node.items()}
        ref = out.get("$ref")
        if isinstance(ref, str) and ref.startswith(_REF_PREFIX):
            out["$ref"] = _DEFS_PREFIX + ref[len(_REF_PREFIX) :]
        return out
    if isinstance(node, list):
        return [_rewrite_refs(v) for v in node]
    return node


def _with_defs(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    """`schema` made self-contained: component refs point into its own `$defs`."""
    needed: list[str] = []
    queue = list(_walk_refs(schema))
    while queue:
        name = queue.pop()
        if name in needed:
            continue
        needed.append(name)
        queue.extend(_walk_refs(components[name]))
    out = _rewrite_refs(schema)
    if needed:
        out["$defs"] = {name: _rewrite_refs(components[name]) for name in sorted(needed)}
    return out


def _resolve(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith(_REF_PREFIX):
        return components[ref[len(_REF_PREFIX) :]]
    return schema


def _is_file(schema: dict[str, Any]) -> bool:
    return schema.get("type") == "string" and (
        schema.get("format") == "binary"
        or schema.get("contentMediaType") == "application/octet-stream"
    )


def _output_schema(
    operation: dict[str, Any], components: dict[str, Any]
) -> dict[str, Any] | None:
    for status in ("200", "201"):
        content = operation.get("responses", {}).get(status, {}).get("content", {})
        schema = content.get("application/json", {}).get("schema")
        if not schema:
            continue
        resolved = _resolve(schema, components)
        if resolved.get("type") == "object":
            # Output schemas need "type": "object" at the top, so inline the model.
            return _with_defs(copy.deepcopy(resolved), components)
        # Structured content must be an object: wrap anything else in `result`.
        return _with_defs(
            {"type": "object", "properties": {"result": schema}, "required": ["result"]},
            components,
        )
    return None


def _annotations(method: str, tags: list[str]) -> types.ToolAnnotations:
    if method == "GET":
        return types.ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    return types.ToolAnnotations(
        readOnlyHint=False,
        # PUT replaces the resource wholesale (e.g. the whole page); DELETE removes it.
        destructiveHint=method in ("PUT", "DELETE"),
        idempotentHint=method in ("PUT", "DELETE"),
        # Importing fetches another site.
        openWorldHint="import" in tags,
    )


def build_operations(spec: dict[str, Any]) -> dict[str, Operation]:
    """Generate a tool for every operation in an OpenAPI spec, minus `EXCLUDED`."""
    components = spec.get("components", {}).get("schemas", {})
    ops: dict[str, Operation] = {}
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            name = operation.get("operationId")
            if not name:
                raise ValueError(f"{method.upper()} {path} needs an operation_id to be a tool")
            if name in EXCLUDED:
                continue
            ops[name] = _build_operation(name, method.upper(), path, operation, components)
    return ops


def _build_operation(
    name: str, method: str, path: str, operation: dict[str, Any], components: dict[str, Any]
) -> Operation:
    properties: dict[str, Any] = {}
    required: list[str] = []
    op = Operation(
        tool=types.Tool(name=name, inputSchema={}),
        method=method,
        path=path,
        admin_only=path.startswith("/api/admin/"),
    )

    for param in operation.get("parameters", []):
        where = param["in"]
        if where not in ("path", "query"):
            continue
        schema = dict(param.get("schema", {}))
        if param.get("description"):
            schema["description"] = param["description"]
        properties[param["name"]] = schema
        if param.get("required"):
            required.append(param["name"])
        (op.path_params if where == "path" else op.query_params).append(param["name"])

    body = operation.get("requestBody")
    if body:
        content = body.get("content", {})
        if "application/json" in content:
            op.body_kind = "json"
            schema = content["application/json"]["schema"]
        elif "multipart/form-data" in content:
            op.body_kind = "multipart"
            schema = content["multipart/form-data"]["schema"]
        else:
            raise ValueError(f"{name}: unsupported request body {sorted(content)}")
        resolved = _resolve(schema, components)
        fields = resolved.get("properties") if resolved.get("type") == "object" else None
        if fields and not set(fields) & set(properties):
            # Flatten the body's fields into the arguments: easier for a model to fill.
            op.body_fields = list(fields)
            for key, value in fields.items():
                if op.body_kind == "multipart" and _is_file(value):
                    op.file_fields.append(key)
                    value = {
                        "type": "string",
                        "contentEncoding": "base64",
                        "title": value.get("title", key),
                        "description": "The image file, base64-encoded (PNG, JPEG, WebP or GIF).",
                    }
                properties[key] = value
            required.extend(r for r in resolved.get("required", []) if r in fields)
        elif op.body_kind == "json":
            properties["body"] = schema
            if body.get("required"):
                required.append("body")
        else:
            raise ValueError(f"{name}: multipart bodies must be objects with distinct fields")

    input_schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        input_schema["required"] = required
    description = operation.get("description") or operation.get("summary") or name
    op.tool = types.Tool(
        name=name,
        title=operation.get("summary"),
        description=description,
        inputSchema=_with_defs(input_schema, components),
        outputSchema=_output_schema(operation, components),
        annotations=_annotations(method, operation.get("tags", [])),
    )
    return op


# --------------------------------------------------------------------------- calls


class ToolCallError(Exception):
    pass


def _sniff_image(data: bytes) -> str:
    for magic, ctype in _IMAGE_MAGIC:
        if data.startswith(magic):
            return ctype
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _build_request(op: Operation, args: dict[str, Any]) -> dict[str, Any]:
    known = set(op.path_params) | set(op.query_params)
    known |= set(op.body_fields) if op.body_fields is not None else {"body"}
    unknown = sorted(set(args) - known)
    if unknown:
        raise ToolCallError(f"Unknown argument(s): {', '.join(unknown)}")

    path = op.path
    for name in op.path_params:
        if args.get(name) in (None, ""):
            raise ToolCallError(f"Missing required argument: {name}")
        path = path.replace("{" + name + "}", quote(str(args[name]), safe=""))
    request: dict[str, Any] = {
        "method": op.method,
        "url": path,
        "params": {k: args[k] for k in op.query_params if args.get(k) is not None},
    }
    if op.body_kind == "json":
        if op.body_fields is None:
            if "body" in args:
                request["json"] = args["body"]
        else:
            request["json"] = {k: args[k] for k in op.body_fields if k in args}
    elif op.body_kind == "multipart":
        files, data = {}, {}
        for key in op.body_fields or []:
            if key not in args or args[key] is None:
                continue
            if key in op.file_fields:
                try:
                    raw = base64.b64decode(str(args[key]), validate=True)
                except (binascii.Error, ValueError):
                    raise ToolCallError(f"{key} must be base64-encoded") from None
                files[key] = (key, raw, _sniff_image(raw))
            else:
                data[key] = str(args[key])
        # Always send multipart, even when only text fields were given.
        request["files"] = files or {"_": ("", b"", "application/octet-stream")}
        request["data"] = data
    return request


def _error_text(resp: httpx2.Response) -> str:
    try:
        detail = resp.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    if isinstance(detail, list):  # FastAPI validation errors
        detail = "; ".join(
            f"{'.'.join(str(p) for p in d.get('loc', []) if p != 'body')}: {d.get('msg')}"
            for d in detail
        )
    return f"{resp.status_code} {detail or resp.reason_phrase or 'Request failed'}"


class NaviMCP:
    """Generated tools for one FastAPI app, and the MCP server that serves them."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self._ops: dict[str, Operation] | None = None
        self.server = Server(
            SERVER_NAME,
            version=settings.app_version,
            title="Navi",
            instructions=INSTRUCTIONS,
            website_url=settings.public_url,
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
        )
        self._http_app = None

    @property
    def operations(self) -> dict[str, Operation]:
        # Built lazily: the OpenAPI schema needs every route registered first.
        if self._ops is None:
            self._ops = build_operations(self.app.openapi())
        return self._ops

    def tools(self, *, admin: bool = True) -> list[types.Tool]:
        return [op.tool for op in self.operations.values() if admin or not op.admin_only]

    async def _user(self, headers: dict[str, str] | None) -> User | None:
        token = _bearer(headers or {})
        if not token:
            return None
        async with AsyncSessionLocal() as db:
            return await user_service.resolve_token(db, token)

    async def _list_tools(self, ctx, params) -> types.ListToolsResult:
        user = await self._user(_ctx_headers(ctx))
        return types.ListToolsResult(tools=self.tools(admin=bool(user and user.is_admin)))

    async def _call_tool(self, ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
        op = self.operations.get(params.name)
        if op is None:
            return _error(f"Unknown tool: {params.name}")
        try:
            request = _build_request(op, dict(params.arguments or {}))
        except ToolCallError as exc:
            return _error(str(exc))
        headers = {}
        token = _bearer(_ctx_headers(ctx))
        if token:
            headers["Authorization"] = f"Bearer {token}"
        transport = httpx2.ASGITransport(app=self.app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://navi.internal") as c:
            resp = await c.request(headers=headers, **request)
        if resp.status_code >= 400:
            return _error(_error_text(resp))
        if resp.status_code == 204 or not resp.content:
            return types.CallToolResult(content=[types.TextContent(type="text", text="Done.")])
        data = resp.json()
        structured = data if isinstance(data, dict) else {"result": data}
        if op.tool.output_schema is None:
            structured = None
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
            structuredContent=structured,
        )

    # ------------------------------------------------------------------ HTTP endpoint

    @contextlib.asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """Run the SDK's session manager for one application lifespan (it can only run
        once, so each lifespan gets a fresh one)."""
        self._http_app = self.server.streamable_http_app(
            streamable_http_path=MCP_PATH,
            stateless_http=True,
            json_response=True,
            # Uploads arrive base64-encoded inside JSON.
            max_request_body_size=max(settings.max_avatar_bytes, settings.max_background_bytes)
            * 2
            + 64 * 1024,
            # Bearer auth (below) is required, so Host-header pinning adds nothing and
            # would break deployments behind arbitrary hostnames.
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        async with self.server.session_manager.run():
            yield
        self._http_app = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self._http_app is None:
            await JSONResponse({"detail": "MCP server not running"}, 503)(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        token = _bearer(headers)
        if not token:
            # Clients that only take a URL (e.g. claude.ai connectors) pass ?key=.
            query = parse_qs(scope.get("query_string", b"").decode())
            token = (query.get("key") or [""])[0].strip()
            if token:
                raw = [(k, v) for k, v in scope.get("headers", []) if k != b"authorization"]
                raw.append((b"authorization", f"Bearer {token}".encode()))
                scope = {**scope, "headers": raw}
        user = await self._user({"authorization": f"Bearer {token}"} if token else None)
        if user is None:
            response = JSONResponse(
                {
                    "detail": "An API key is required: send 'Authorization: Bearer navi_…'. "
                    "Create one in Navi under Account → AI tools."
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        # The SDK app routes on the full path; normalise a trailing slash.
        if scope["path"] == MCP_PATH + "/":
            scope = {**scope, "path": MCP_PATH}
        await self._http_app(scope, receive, send)


def _ctx_headers(ctx: Any) -> dict[str, str]:
    """The HTTP request headers behind a tool request (empty off HTTP)."""
    request = getattr(ctx, "request", None)
    headers = getattr(request, "headers", None) or {}
    return {k.lower(): v for k, v in headers.items()}


def _bearer(headers: dict[str, str]) -> str | None:
    scheme, _, token = (headers.get("authorization") or "").partition(" ")
    token = token.strip()
    return token if scheme.lower() == "bearer" and token else None


def _error(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], isError=True)


def tools_document(navi: NaviMCP) -> dict[str, Any]:
    """The published description of the MCP server (docs/mcp-tools.json)."""
    return {
        "server": SERVER_NAME,
        "transport": "streamable-http",
        "path": MCP_PATH,
        "auth": "Authorization: Bearer <API key>",
        "generated_from": "openapi.json (one tool per operationId)",
        "excluded_operations": dict(sorted(EXCLUDED.items())),
        "tools": [
            t.model_dump(mode="json", by_alias=True, exclude_none=True)
            for t in sorted(navi.tools(), key=lambda t: t.name)
        ],
    }

