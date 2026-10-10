from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

POST_KINDS = ("article", "note")

# Weighted so a match in the title outranks one buried in the body.
POST_SEARCH_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(summary, '')), 'B') || "
    "setweight(to_tsvector('english', coalesce(body_md, '')), 'C')"
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Post(Base):
    """Something Anish wrote: a long-form article or a short note."""

    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint("kind IN ('article', 'note')", name="posts_kind_check"),
        Index("ix_posts_tags", "tags", postgresql_using="gin"),
        Index("ix_posts_search", "search", postgresql_using="gin"),
        Index("ix_posts_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, server_default="article")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    body_md: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    reading_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    search: Mapped[str] = mapped_column(
        TSVECTOR, Computed(POST_SEARCH_SQL, persisted=True), nullable=True
    )


class Link(Base):
    """An article by someone else, saved with what Anish took from it."""

    __tablename__ = "links"
    __table_args__ = (Index("ix_links_tags", "tags", postgresql_using="gin"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False, server_default="")
    takeaway: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
