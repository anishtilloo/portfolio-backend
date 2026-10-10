"""Initial schema: users, posts, links

Revision ID: 0001
Revises:
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Written out here rather than imported from the app, so this migration keeps
# meaning the same thing even if the model changes later.
POST_SEARCH_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(summary, '')), 'B') || "
    "setweight(to_tsvector('english', coalesce(body_md, '')), 'C')"
)

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False, server_default="article"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False, unique=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("body_md", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("reading_minutes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        # Kept up to date by Postgres itself, so search never drifts from the content.
        sa.Column(
            "search",
            postgresql.TSVECTOR(),
            sa.Computed(POST_SEARCH_SQL, persisted=True),
            nullable=True,
        ),
        sa.CheckConstraint("kind IN ('article', 'note')", name="posts_kind_check"),
    )
    op.create_index("ix_posts_tags", "posts", ["tags"], postgresql_using="gin")
    op.create_index("ix_posts_search", "posts", ["search"], postgresql_using="gin")
    op.create_index("ix_posts_published_at", "posts", ["published_at"])

    op.create_table(
        "links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("source", sa.String(120), nullable=False, server_default=""),
        sa.Column("takeaway", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_links_tags", "links", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("links")
    op.drop_table("posts")
    op.drop_table("users")
