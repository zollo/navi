"""Page themes, background images, the curated gallery and admins.

Revision ID: 0002_page_themes
Revises: 0001_initial
Create Date: 2026-11-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_page_themes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backgrounds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("image", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("dark", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.add_column("pages", sa.Column("theme", json_type, nullable=True))
    op.add_column("pages", sa.Column("background", sa.LargeBinary(), nullable=True))
    op.add_column("pages", sa.Column("background_content_type", sa.String(64), nullable=True))
    op.add_column(
        "pages",
        sa.Column("background_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("pages", "background_version", server_default=None)
    op.add_column("pages", sa.Column("background_id", sa.Uuid(), nullable=True))
    op.create_index("ix_pages_background_id", "pages", ["background_id"])
    op.create_foreign_key(
        "fk_pages_background_id_backgrounds",
        "pages",
        "backgrounds",
        ["background_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("users", "is_admin", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "is_admin")
    op.drop_constraint("fk_pages_background_id_backgrounds", "pages", type_="foreignkey")
    op.drop_index("ix_pages_background_id", table_name="pages")
    op.drop_column("pages", "background_id")
    op.drop_column("pages", "background_version")
    op.drop_column("pages", "background_content_type")
    op.drop_column("pages", "background")
    op.drop_column("pages", "theme")
    op.drop_table("backgrounds")
