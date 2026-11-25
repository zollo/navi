"""Write the OpenAPI spec to a file.

    python -m app.openapi_export ../docs/openapi.json \
        [--mcp-tools ../docs/mcp-tools.json] [--version X.Y.Z]

CI checks that both files in docs/ are current, and attaches versioned copies to
every GitHub release. The MCP tools are generated from the OpenAPI schema, so they
change whenever the API does.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mcp-tools", type=Path, default=None, help="Also write MCP tools.")
    parser.add_argument("--version", default=None, help="Override info.version.")
    args = parser.parse_args()

    from app.main import app, mcp

    spec = app.openapi()
    if args.version:
        spec["info"]["version"] = args.version
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(spec, indent=2, sort_keys=False) + "\n")
    print(f"Wrote {args.output} ({len(spec['paths'])} paths)")

    if args.mcp_tools:
        from app.mcp_server import tools_document

        doc = tools_document(mcp)
        args.mcp_tools.parent.mkdir(parents=True, exist_ok=True)
        args.mcp_tools.write_text(json.dumps(doc, indent=2, sort_keys=False) + "\n")
        print(f"Wrote {args.mcp_tools} ({len(doc['tools'])} tools)")


if __name__ == "__main__":
    main()
