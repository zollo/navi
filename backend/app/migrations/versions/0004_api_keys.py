"""Personal API keys (REST API and MCP server).

Revision ID: 0004_api_keys
Revises: 0003_custom_domains
Create Date: 2026-11-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_api_keys"
down_revision = "0003_custom_domains"
branch_labels = None
depends_on = None

# Top-level paths this release claims; existing pages with these handles move to
# "<handle>-<6 hex>" (the old URL would hit the MCP endpoint / setup page anyway).
NEWLY_RESERVED = ("integrations", "mcp")


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    bind = op.get_bind()
    pages = sa.table("pages", sa.column("id", sa.Uuid()), sa.column("handle", sa.String()))
    rows = bind.execute(sa.select(pages.c.id, pages.c.handle).where(pages.c.handle.in_(NEWLY_RESERVED)))
    for page_id, handle in rows.fetchall():
        new = f"{handle}-{page_id.hex[:6]}"
        print(f"Renaming page handle {handle!r} to {new!r}: /{handle} is now reserved")
        bind.execute(sa.update(pages).where(pages.c.id == page_id).values(handle=new))


def downgrade() -> None:
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
