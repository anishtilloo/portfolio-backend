"""Writing endpoints. Every route here needs a signed-in user."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import Session, get_current_user
from app.models import Link, Post
from app.schemas import (
    LinkCreate,
    LinkOut,
    LinkUpdate,
    PostCreate,
    PostDetail,
    PostKind,
    PostPage,
    PostUpdate,
)
from app.text import reading_minutes, slugify

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_current_user)])


async def unique_slug(session: AsyncSession, wanted: str, ignore_id: int | None = None) -> str:
    """Return `wanted`, or `wanted-2`, `wanted-3`… if it is taken."""
    taken = select(Post.slug).where((Post.slug == wanted) | Post.slug.like(f"{wanted}-%"))
    if ignore_id is not None:
        taken = taken.where(Post.id != ignore_id)
    existing = set(await session.scalars(taken))
    if wanted not in existing:
        return wanted
    n = 2
    while f"{wanted}-{n}" in existing:
        n += 1
    return f"{wanted}-{n}"


async def load_post(session: AsyncSession, post_id: int) -> Post:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This post no longer exists")
    return post


async def commit_post(session: AsyncSession, post: Post) -> Post:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Another post already uses that address"
        ) from exc
    await session.refresh(post)
    return post


@router.get("/posts", response_model=PostPage)
async def list_all_posts(
    session: Session,
    kind: PostKind | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PostPage:
    """Drafts and published posts, most recently edited first."""
    base = select(Post)
    if kind:
        base = base.where(Post.kind == kind)
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = await session.scalars(
        base.order_by(Post.updated_at.desc(), Post.id.desc()).limit(limit).offset(offset)
    )
    return PostPage(items=list(rows), total=total or 0)


@router.post("/posts", response_model=PostDetail, status_code=status.HTTP_201_CREATED)
async def create_post(data: PostCreate, session: Session) -> Post:
    slug = await unique_slug(session, data.slug or slugify(data.title))
    post = Post(
        kind=data.kind,
        title=data.title,
        slug=slug,
        summary=data.summary,
        body_md=data.body_md,
        tags=data.tags,
        reading_minutes=reading_minutes(data.body_md),
        published=data.published,
        published_at=datetime.now(UTC) if data.published else None,
    )
    session.add(post)
    return await commit_post(session, post)


@router.get("/posts/{post_id}", response_model=PostDetail)
async def get_any_post(post_id: int, session: Session) -> Post:
    return await load_post(session, post_id)


@router.patch("/posts/{post_id}", response_model=PostDetail)
async def update_post(post_id: int, data: PostUpdate, session: Session) -> Post:
    post = await load_post(session, post_id)
    changes = data.model_dump(exclude_unset=True)

    if "slug" in changes:
        wanted = changes.pop("slug") or slugify(changes.get("title") or post.title)
        if wanted != post.slug:
            post.slug = await unique_slug(session, wanted, ignore_id=post.id)

    for field in ("kind", "title", "summary", "body_md", "tags"):
        if changes.get(field) is not None:
            setattr(post, field, changes[field])
    if changes.get("body_md") is not None:
        post.reading_minutes = reading_minutes(post.body_md)

    if changes.get("published") is not None:
        post.published = changes["published"]
        # Keep the original date if a post is unpublished and published again.
        if post.published and post.published_at is None:
            post.published_at = datetime.now(UTC)

    return await commit_post(session, post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, session: Session) -> Response:
    post = await load_post(session, post_id)
    await session.delete(post)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def load_link(session: AsyncSession, link_id: int) -> Link:
    link = await session.get(Link, link_id)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This saved article no longer exists")
    return link


@router.post("/links", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(data: LinkCreate, session: Session) -> Link:
    link = Link(
        url=str(data.url),
        title=data.title,
        source=data.source,
        takeaway=data.takeaway,
        tags=data.tags,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


@router.patch("/links/{link_id}", response_model=LinkOut)
async def update_link(link_id: int, data: LinkUpdate, session: Session) -> Link:
    link = await load_link(session, link_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(link, field, str(value) if field == "url" else value)
    await session.commit()
    await session.refresh(link)
    return link


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(link_id: int, session: Session) -> Response:
    link = await load_link(session, link_id)
    await session.delete(link)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
