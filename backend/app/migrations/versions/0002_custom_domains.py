"""Custom domains for pages.

Revision ID: 0002_custom_domains
Revises: 0001_initial
Create Date: 2026-11-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_custom_domains"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "custom_domains",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("page_id", sa.Uuid(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("hostname", sa.String(253), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_custom_domains_hostname", "custom_domains", ["hostname"])
    # Several pages may claim a hostname, but only one can verify it.
    op.create_index(
        "uq_custom_domains_verified_hostname",
        "custom_domains",
        ["hostname"],
        unique=True,
        postgresql_where=sa.text("verified_at IS NOT NULL"),
        sqlite_where=sa.text("verified_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_custom_domains_verified_hostname", table_name="custom_domains")
    op.drop_index("ix_custom_domains_hostname", table_name="custom_domains")
    op.drop_table("custom_domains")
