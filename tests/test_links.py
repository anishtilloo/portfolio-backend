LINK = {
    "url": "https://www.postgresql.org/docs/current/arrays.html",
    "title": "Arrays",
    "source": "PostgreSQL docs",
    "takeaway": "Empty array and NULL are different things.",
    "tags": ["PostgreSQL"],
}


async def test_save_edit_and_remove_an_article(client, auth):
    created = await client.post("/api/admin/links", json=LINK, headers=auth)
    assert created.status_code == 201
    link = created.json()
    assert link["tags"] == ["postgresql"]

    public = (await client.get("/api/links")).json()
    assert [item["title"] for item in public] == ["Arrays"]

    edited = await client.patch(
        f"/api/admin/links/{link['id']}", json={"takeaway": "Updated"}, headers=auth
    )
    assert edited.json()["takeaway"] == "Updated"
    assert edited.json()["url"] == LINK["url"]

    assert (await client.delete(f"/api/admin/links/{link['id']}", headers=auth)).status_code == 204
    assert (await client.get("/api/links")).json() == []


async def test_only_web_addresses_are_accepted(client, auth):
    for bad in ("javascript:alert(1)", "not a url", "ftp://example.com/file"):
        response = await client.post("/api/admin/links", json=LINK | {"url": bad}, headers=auth)
        assert response.status_code == 422, bad


async def test_filter_links_by_tag(client, auth):
    await client.post("/api/admin/links", json=LINK, headers=auth)
    await client.post(
        "/api/admin/links",
        json=LINK | {"title": "Watchers", "url": "https://vuejs.org/guide", "tags": ["vue"]},
        headers=auth,
    )
    vue = (await client.get("/api/links", params={"tag": "vue"})).json()
    assert [item["title"] for item in vue] == ["Watchers"]


async def test_seed_fills_an_empty_blog_once(client, session):
    from app.seed import LINKS, POSTS, seed

    assert await seed(session) == {"posts": len(POSTS), "links": len(LINKS)}
    assert await seed(session) == {"posts": 0, "links": 0}

    posts = (await client.get("/api/posts")).json()
    assert posts["total"] == len(POSTS)
    first = (await client.get(f"/api/posts/{posts['items'][0]['slug']}")).json()
    assert first["body_md"].strip()
    assert len((await client.get("/api/links")).json()) == len(LINKS)


async def test_health(client):
    assert (await client.get("/api/health")).json() == {"status": "ok"}
