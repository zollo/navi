"""Initial schema: users, pages, social links, sections and links.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "pages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("handle", sa.String(30), nullable=False),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("tagline", sa.Text(), nullable=False),
        sa.Column("avatar", sa.LargeBinary(), nullable=True),
        sa.Column("avatar_content_type", sa.String(64), nullable=True),
        sa.Column("avatar_version", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_pages_handle", "pages", ["handle"], unique=True)

    op.create_table(
        "social_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("page_id", sa.Uuid(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("icon", sa.String(32), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
    )
    op.create_index("ix_social_links_page_id", "social_links", ["page_id"])

    op.create_table(
        "sections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("page_id", sa.Uuid(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(80), nullable=False),
    )
    op.create_index("ix_sections_page_id", "sections", ["page_id"])

    op.create_table(
        "links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("section_id", sa.Uuid(), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("icon", sa.String(32), nullable=False),
    )
    op.create_index("ix_links_section_id", "links", ["section_id"])


def downgrade() -> None:
    op.drop_table("links")
    op.drop_table("sections")
    op.drop_table("social_links")
    op.drop_table("pages")
    op.drop_table("users")
