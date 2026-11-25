"""Small admin commands, run inside the backend container.

    python -m app.manage admin someone@example.com           # make an admin
    python -m app.manage admin someone@example.com --revoke  # take it away

Admins manage the curated background gallery. ADMIN_EMAILS grants the role on
sign-in too; revoking only sticks once the email is out of ADMIN_EMAILS.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.errors import NaviError
from app.db import AsyncSessionLocal, engine
from app.services import user_service


async def _set_admin(email: str, is_admin: bool) -> None:
    async with AsyncSessionLocal() as db:
        user = await user_service.set_admin(db, email, is_admin)
    await engine.dispose()
    print(f"{user.email} is {'now' if user.is_admin else 'no longer'} an admin")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.manage", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("admin", help="Grant or revoke the admin role")
    admin.add_argument("email")
    admin.add_argument("--revoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        asyncio.run(_set_admin(args.email.strip().lower(), not args.revoke))
    except NaviError as exc:
        print(exc.detail, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
