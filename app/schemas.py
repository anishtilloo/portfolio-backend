import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
)

PostKind = Literal["article", "note"]

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def clean_tags(tags: list[str]) -> list[str]:
    """Lowercase, trim and de-duplicate tags while keeping their order."""
    seen: dict[str, None] = {}
    for tag in tags:
        tag = re.sub(r"\s+", " ", tag.strip().lower())
        if not tag:
            continue
        if len(tag) > 40:
            raise ValueError("A tag can be at most 40 characters")
        seen.setdefault(tag)
    if len(seen) > 12:
        raise ValueError("Use at most 12 tags")
    return list(seen)


Tags = Annotated[list[str], AfterValidator(clean_tags)]


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class PostBase(BaseModel):
    kind: PostKind = "article"
    title: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    summary: str = Field(default="", max_length=500)
    body_md: str = Field(default="", max_length=200_000)
    tags: Tags = []
    published: bool = False

    @field_validator("title", "summary")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("Give the post a title")
        return value

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        value = value.strip().lower()
        if not SLUG_RE.match(value):
            raise ValueError("Use lowercase letters, numbers and single hyphens in the address")
        return value


class PostCreate(PostBase):
    pass


class PostUpdate(PostBase):
    """Every field optional: send only what changed."""

    kind: PostKind | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    body_md: str | None = Field(default=None, max_length=200_000)
    tags: Tags | None = None
    published: bool | None = None

    @field_validator("title", "summary")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Give the post a title")
        return value


class PostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: PostKind
    title: str
    slug: str
    summary: str
    tags: list[str]
    reading_minutes: int
    published: bool
    published_at: datetime | None
    updated_at: datetime


class PostDetail(PostSummary):
    body_md: str
    created_at: datetime


class PostPage(BaseModel):
    items: list[PostSummary]
    total: int


class TagCount(BaseModel):
    tag: str
    count: int


class LinkBase(BaseModel):
    url: HttpUrl
    title: str = Field(min_length=1, max_length=300)
    source: str = Field(default="", max_length=120)
    takeaway: str = Field(default="", max_length=2000)
    tags: Tags = []

    @field_validator("title", "source", "takeaway")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("Give the article a title")
        return value


class LinkCreate(LinkBase):
    pass


class LinkUpdate(LinkBase):
    url: HttpUrl | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    source: str | None = Field(default=None, max_length=120)
    takeaway: str | None = Field(default=None, max_length=2000)
    tags: Tags | None = None

    @field_validator("title", "source", "takeaway")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Give the article a title")
        return value


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    url: str
    title: str
    source: str
    takeaway: str
    tags: list[str]
    created_at: datetime
