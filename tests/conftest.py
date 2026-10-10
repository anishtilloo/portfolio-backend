"""Tests run against a real Postgres database, because the app leans on
Postgres features (arrays, full-text search) that SQLite cannot stand in for.

By default they use a database called `portfolio_test` next to your dev one.
Create it once:

    docker compose exec db createdb -U portfolio portfolio_test

or point TEST_DATABASE_URL at any empty database you like.
"""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://portfolio:portfolio@localhost:5432/portfolio_test",
)
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402, F401
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password, login_throttle  # noqa: E402

ADMIN_EMAIL = "anish@example.com"
ADMIN_PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="session", autouse=True)
async def schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables(schema):
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, posts, links RESTART IDENTITY"))
    login_throttle.reset()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def session():
    async with SessionLocal() as s:
        yield s


@pytest.fixture
async def admin(session) -> User:
    user = User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD))
    session.add(user)
    await session.commit()
    return user


@pytest.fixture
async def auth(client, admin) -> dict[str, str]:
    """Authorization headers for the signed-in admin."""
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def make_post(client, auth):
    async def _make(**overrides) -> dict:
        payload = {
            "title": "Hello Postgres",
            "summary": "A first post",
            "body_md": "Some **markdown** about arrays.",
            "tags": ["postgresql"],
            "published": True,
        } | overrides
        response = await client.post("/api/admin/posts", json=payload, headers=auth)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
