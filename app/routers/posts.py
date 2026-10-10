"""Public, read-only blog endpoints. Only published posts are visible here."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select

from app.deps import Session
from app.models import Post
from app.schemas import PostDetail, PostKind, PostPage, TagCount
from app.text import escape_like

router = APIRouter(prefix="/api", tags=["blog"])


def filter_posts(
    query: Select, *, kind: str | None, tag: str | None, q: str | None
) -> tuple[Select, list]:
    """Apply the list filters. Returns the query and the ordering to use."""
    order = [Post.published_at.desc().nulls_last(), Post.id.desc()]
    if kind:
        query = query.where(Post.kind == kind)
    if tag:
        query = query.where(Post.tags.contains([tag.strip().lower()]))
    if q and q.strip():
        q = q.strip()
        ts_query = func.websearch_to_tsquery("english", q)
        # Full-text search finds whole words; the ILIKE lets a half-typed title match too.
        query = query.where(
            or_(
                Post.search.op("@@")(ts_query),
                Post.title.ilike(f"%{escape_like(q)}%", escape="\\"),
            )
        )
        order = [func.ts_rank(Post.search, ts_query).desc(), *order]
    return query, order


@router.get("/posts", response_model=PostPage)
async def list_posts(
    session: Session,
    kind: PostKind | None = None,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PostPage:
    base, order = filter_posts(
        select(Post).where(Post.published.is_(True)), kind=kind, tag=tag, q=q
    )
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = await session.scalars(base.order_by(*order).limit(limit).offset(offset))
    return PostPage(items=list(rows), total=total or 0)


@router.get("/posts/{slug}", response_model=PostDetail)
async def get_post(slug: str, session: Session) -> Post:
    post = await session.scalar(select(Post).where(Post.slug == slug, Post.published.is_(True)))
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No published post at this address")
    return post


@router.get("/tags", response_model=list[TagCount])
async def list_tags(session: Session) -> list[TagCount]:
    """Tags used by published posts, most used first."""
    tag = func.unnest(Post.tags).label("tag")
    per_post = select(tag).where(Post.published.is_(True)).subquery()
    rows = await session.execute(
        select(per_post.c.tag, func.count().label("count"))
        .group_by(per_post.c.tag)
        .order_by(func.count().desc(), per_post.c.tag)
    )
    return [TagCount(tag=row.tag, count=row.count) for row in rows]
