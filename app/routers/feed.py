from email.utils import format_datetime
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.config import get_settings
from app.deps import Session
from app.models import Post

router = APIRouter(prefix="/api", tags=["blog"])


@router.get("/feed.xml", include_in_schema=False)
async def rss_feed(session: Session) -> Response:
    """RSS 2.0 feed of the 30 most recent published posts."""
    settings = get_settings()
    site = settings.site_url.rstrip("/")
    posts = await session.scalars(
        select(Post)
        .where(Post.published.is_(True))
        .order_by(Post.published_at.desc().nulls_last(), Post.id.desc())
        .limit(30)
    )

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = settings.site_title
    ET.SubElement(channel, "link").text = f"{site}/blog"
    ET.SubElement(channel, "description").text = settings.site_description
    ET.SubElement(channel, "language").text = "en"

    for post in posts:
        url = f"{site}/blog/{post.slug}"
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = post.title
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "guid", isPermaLink="true").text = url
        ET.SubElement(item, "description").text = post.summary
        for tag in post.tags:
            ET.SubElement(item, "category").text = tag
        if post.published_at:
            ET.SubElement(item, "pubDate").text = format_datetime(post.published_at)

    body = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="utf-8")
    return Response(content=body, media_type="application/rss+xml")
