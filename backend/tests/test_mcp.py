"""MCP server: auth, tools generated from the OpenAPI schema, and real calls."""
from __future__ import annotations

import base64
import json

from app.main import app, mcp
from app.mcp_server import EXCLUDED, build_operations, tools_document

from .test_pages import PAGE, PNG

MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def _key(client, headers) -> str:
    return client.post("/api/api-keys", json={"name": "test"}, headers=headers).json()["key"]


def _mcp_headers(client, headers) -> dict[str, str]:
    return {**MCP_HEADERS, "Authorization": f"Bearer {_key(client, headers)}"}


def _rpc(client, headers, method, params=None, url="/mcp"):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    resp = client.post(url, headers=headers, content=json.dumps(body))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _initialize(client, headers, url="/mcp"):
    return _rpc(
        client,
        headers,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1"},
        },
        url=url,
    )


def _tools(client, headers) -> dict[str, dict]:
    return {t["name"]: t for t in _rpc(client, headers, "tools/list", {})["result"]["tools"]}


def _call(client, headers, name, arguments=None):
    return _rpc(client, headers, "tools/call", {"name": name, "arguments": arguments or {}})[
        "result"
    ]


# ---------------------------------------------------------------- drift checks


def test_every_operation_is_a_tool_or_excluded_with_a_reason():
    """New routes become tools automatically; exclusions must name real operations."""
    spec = app.openapi()
    operation_ids = {
        op["operationId"] for item in spec["paths"].values() for op in item.values()
    }
    assert set(EXCLUDED) <= operation_ids, f"stale EXCLUDED: {set(EXCLUDED) - operation_ids}"
    assert all(reason.strip() for reason in EXCLUDED.values())
    tools = {t.name for t in mcp.tools()}
    assert tools == operation_ids - set(EXCLUDED)


def test_tools_carry_the_api_contract():
    tools = {t.name: t for t in mcp.tools()}
    save = tools["save_my_page"]
    # The request body's fields are the tool's arguments, with the API's own schema.
    assert save.input_schema["required"] == ["handle"]
    assert save.input_schema["properties"]["sections"]["items"]["$ref"] == "#/$defs/SectionIn"
    assert "SectionIn" in save.input_schema["$defs"]
    assert save.annotations.destructive_hint is True
    assert tools["get_my_page"].annotations.read_only_hint is True
    assert tools["check_handle"].input_schema["required"] == ["handle"]
    assert tools["upload_my_avatar"].input_schema["properties"]["file"]["contentEncoding"] == (
        "base64"
    )
    assert tools["import_linktree"].annotations.open_world_hint is True
    # Descriptions come from the route docstrings.
    assert "Send the whole page" in save.description


def test_published_tool_list_is_current():
    """docs/mcp-tools.json must match what the server serves (CI regenerates it too)."""
    from pathlib import Path

    published = Path(__file__).resolve().parents[2] / "docs" / "mcp-tools.json"
    expected = json.loads(json.dumps(tools_document(mcp)))
    assert json.loads(published.read_text()) == expected, (
        "docs/mcp-tools.json is stale: run `make openapi`"
    )


def test_build_operations_rejects_operations_without_ids():
    import pytest

    spec = {"paths": {"/api/x": {"get": {"responses": {}}}}}
    with pytest.raises(ValueError, match="operation_id"):
        build_operations(spec)


# ---------------------------------------------------------------- endpoint


def test_mcp_requires_a_key(client, alice):
    assert client.post("/mcp", headers=MCP_HEADERS, content="{}").status_code == 401
    bad = {**MCP_HEADERS, "Authorization": "Bearer navi_nope"}
    resp = client.post("/mcp", headers=bad, content="{}")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_tools_list_and_admin_tools(client, alice, admin):
    headers = _mcp_headers(client, alice)
    init = _initialize(client, headers)
    assert init["result"]["serverInfo"]["name"] == "navi"
    assert "save_my_page" in init["result"]["instructions"]
    names = set(_tools(client, headers))
    assert {"get_my_page", "save_my_page", "list_icons", "check_handle"} <= names
    assert "create_background" not in names
    assert "login" not in names and "create_api_key" not in names

    admin_tools = _tools(client, _mcp_headers(client, admin))
    assert "create_background" in admin_tools


def test_edit_a_page_through_mcp(client, alice):
    headers = _mcp_headers(client, alice)
    _initialize(client, headers)

    missing = _call(client, headers, "get_my_page")
    assert missing["isError"] is True and missing["content"][0]["text"].startswith("404")

    saved = _call(client, headers, "save_my_page", PAGE)
    assert not saved.get("isError"), saved
    assert saved["structuredContent"]["handle"] == "the.saasy.engineer"

    page = _call(client, headers, "get_my_page")["structuredContent"]
    page_in = {
        "handle": page["handle"],
        "title": "New title",
        "sections": [{"title": "Only", "links": [{"title": "Site", "url": "https://x.dev"}]}],
    }
    assert _call(client, headers, "save_my_page", page_in)["structuredContent"]["title"] == (
        "New title"
    )
    # The REST API sees the same page.
    public = client.get("/api/pages/the.saasy.engineer").json()
    assert public["title"] == "New title" and len(public["sections"]) == 1

    # API validation errors come back as readable tool errors.
    bad = _call(
        client,
        headers,
        "save_my_page",
        {**page_in, "sections": [{"links": [{"title": "x", "url": "javascript:alert(1)"}]}]},
    )
    assert bad["isError"] is True and "url" in bad["content"][0]["text"]
    unknown = _call(client, headers, "save_my_page", {**page_in, "colour": "red"})
    assert unknown["isError"] is True and "colour" in unknown["content"][0]["text"]

    # Path parameters, list results and public tools.
    check = _call(client, headers, "check_handle", {"handle": "the.saasy.engineer"})
    assert check["structuredContent"]["available"] is True  # it's yours
    icons = _call(client, headers, "list_icons")["structuredContent"]["icons"]
    assert "github" in icons


def test_upload_avatar_as_base64(client, alice):
    headers = _mcp_headers(client, alice)
    _call(client, headers, "save_my_page", PAGE)
    result = _call(
        client, headers, "upload_my_avatar", {"file": base64.b64encode(PNG).decode()}
    )
    assert not result.get("isError"), result
    assert client.get(result["structuredContent"]["avatar_url"]).content == PNG
    bad = _call(client, headers, "upload_my_avatar", {"file": "not base64!"})
    assert bad["isError"] is True


def test_delete_returns_done(client, alice):
    headers = _mcp_headers(client, alice)
    _call(client, headers, "save_my_page", PAGE)
    result = _call(client, headers, "delete_my_page")
    assert result["content"][0]["text"] == "Done."
    assert client.get("/api/pages/the.saasy.engineer").status_code == 404


def test_key_in_the_url(client, alice):
    """For clients that only take a URL (claude.ai connectors)."""
    key = _key(client, alice)
    url = f"/mcp?key={key}"
    _initialize(client, MCP_HEADERS, url=url)
    resp = client.post(
        url,
        headers=MCP_HEADERS,
        content=json.dumps(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "whoami", "arguments": {}}}
        ),
    )
    assert resp.json()["result"]["structuredContent"]["email"] == "alice@example.com"


def test_session_tokens_cannot_be_used_to_reach_key_management(client, alice):
    """Even a password session can't create keys over MCP: those routes aren't tools."""
    headers = {**MCP_HEADERS, **alice}
    result = _call(client, headers, "create_api_key", {"name": "x"})
    assert result["isError"] is True and "Unknown tool" in result["content"][0]["text"]
