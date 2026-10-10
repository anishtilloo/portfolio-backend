"""Public reading list: articles by other people, with a takeaway."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.deps import Session
from app.models import Link
from app.schemas import LinkOut

router = APIRouter(prefix="/api", tags=["reading list"])


@router.get("/links", response_model=list[LinkOut])
async def list_links(
    session: Session,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Link]:
    query = select(Link)
    if tag:
        query = query.where(Link.tags.contains([tag.strip().lower()]))
    rows = await session.scalars(
        query.order_by(Link.created_at.desc(), Link.id.desc()).limit(limit).offset(offset)
    )
    return list(rows)
