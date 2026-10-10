from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


async def test_login_returns_a_token_that_works(client, admin):
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL.upper(), "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_EMAIL


async def test_wrong_password_and_unknown_email_look_the_same(client, admin):
    wrong = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": "nope-nope-nope"}
    )
    unknown = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": ADMIN_PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_repeated_failures_are_throttled(client, admin):
    for _ in range(5):
        response = await client.post(
            "/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-password"}
        )
        assert response.status_code == 401

    blocked = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


async def test_admin_routes_need_a_valid_token(client):
    assert (await client.get("/api/admin/posts")).status_code == 401
    assert (await client.post("/api/admin/posts", json={"title": "x"})).status_code == 401
    assert (await client.post("/api/admin/links", json={})).status_code == 401
    forged = {"Authorization": "Bearer not.a.token"}
    assert (await client.get("/api/admin/posts", headers=forged)).status_code == 401
    assert (await client.delete("/api/admin/posts/1", headers=forged)).status_code == 401
