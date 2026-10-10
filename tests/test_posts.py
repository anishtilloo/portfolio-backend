async def test_create_generates_slug_and_reading_time(make_post):
    post = await make_post(title="Arrays in PostgreSQL: a Primer!", body_md="word " * 500)
    assert post["slug"] == "arrays-in-postgresql-a-primer"
    assert post["reading_minutes"] == 3
    assert post["published_at"] is not None


async def test_duplicate_titles_get_numbered_slugs(make_post):
    first = await make_post(title="Same title")
    second = await make_post(title="Same title")
    third = await make_post(title="Same title")
    assert [first["slug"], second["slug"], third["slug"]] == [
        "same-title",
        "same-title-2",
        "same-title-3",
    ]


async def test_drafts_are_hidden_from_the_public(client, auth, make_post):
    draft = await make_post(title="Still thinking", published=False)
    assert draft["published_at"] is None

    listing = await client.get("/api/posts")
    assert listing.json() == {"items": [], "total": 0}
    assert (await client.get(f"/api/posts/{draft['slug']}")).status_code == 404
    assert (await client.get("/api/tags")).json() == []

    # ...but the author still sees it.
    mine = await client.get("/api/admin/posts", headers=auth)
    assert [p["title"] for p in mine.json()["items"]] == ["Still thinking"]


async def test_publish_then_unpublish_keeps_the_original_date(client, auth, make_post):
    draft = await make_post(published=False)
    url = f"/api/admin/posts/{draft['id']}"

    published = (await client.patch(url, json={"published": True}, headers=auth)).json()
    assert published["published_at"] is not None
    assert (await client.get(f"/api/posts/{draft['slug']}")).status_code == 200

    await client.patch(url, json={"published": False}, headers=auth)
    assert (await client.get(f"/api/posts/{draft['slug']}")).status_code == 404

    again = (await client.patch(url, json={"published": True}, headers=auth)).json()
    assert again["published_at"] == published["published_at"]


async def test_partial_update_leaves_other_fields_alone(client, auth, make_post):
    post = await make_post(title="Before", tags=["vue", "typescript"])
    response = await client.patch(
        f"/api/admin/posts/{post['id']}", json={"title": "After"}, headers=auth
    )
    updated = response.json()
    assert updated["title"] == "After"
    assert updated["slug"] == "before"  # addresses don't change behind your back
    assert updated["tags"] == ["vue", "typescript"]
    assert updated["body_md"] == post["body_md"]


async def test_changing_the_slug_to_a_taken_one_is_made_unique(client, auth, make_post):
    await make_post(title="First")
    second = await make_post(title="Second")
    response = await client.patch(
        f"/api/admin/posts/{second['id']}", json={"slug": "first"}, headers=auth
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "first-2"


async def test_filter_by_kind_and_tag(client, make_post):
    await make_post(title="Long read", kind="article", tags=["PostgreSQL", " sql "])
    await make_post(title="Quick tip", kind="note", tags=["vue"])

    notes = (await client.get("/api/posts", params={"kind": "note"})).json()
    assert [p["title"] for p in notes["items"]] == ["Quick tip"]

    tagged = (await client.get("/api/posts", params={"tag": "postgresql"})).json()
    assert [p["title"] for p in tagged["items"]] == ["Long read"]
    assert tagged["items"][0]["tags"] == ["postgresql", "sql"]  # cleaned on the way in

    tags = (await client.get("/api/tags")).json()
    assert {t["tag"]: t["count"] for t in tags} == {"postgresql": 1, "sql": 1, "vue": 1}


async def test_search_matches_body_words_and_partial_titles(client, make_post):
    await make_post(title="Watchers in Vue", body_md="How to cancel a stale request.")
    await make_post(title="Array parameters", body_md="Filtering with ANY in functions.")

    by_body = (await client.get("/api/posts", params={"q": "stale requests"})).json()
    assert [p["title"] for p in by_body["items"]] == ["Watchers in Vue"]  # stemming: requests

    by_prefix = (await client.get("/api/posts", params={"q": "Arr"})).json()
    assert [p["title"] for p in by_prefix["items"]] == ["Array parameters"]

    literal = (await client.get("/api/posts", params={"q": "100%_"})).json()
    assert literal["total"] == 0  # wildcards in the query are not wildcards


async def test_pagination(client, make_post):
    for n in range(5):
        await make_post(title=f"Post {n}")
    page = (await client.get("/api/posts", params={"limit": 2, "offset": 2})).json()
    assert page["total"] == 5
    assert [p["title"] for p in page["items"]] == ["Post 2", "Post 1"]


async def test_validation_messages(client, auth):
    blank = await client.post("/api/admin/posts", json={"title": "   "}, headers=auth)
    assert blank.status_code == 422

    bad_slug = await client.post(
        "/api/admin/posts", json={"title": "Fine", "slug": "Not A Slug"}, headers=auth
    )
    assert bad_slug.status_code == 422

    bad_kind = await client.post(
        "/api/admin/posts", json={"title": "Fine", "kind": "tweet"}, headers=auth
    )
    assert bad_kind.status_code == 422


async def test_delete(client, auth, make_post):
    post = await make_post()
    url = f"/api/admin/posts/{post['id']}"
    assert (await client.delete(url, headers=auth)).status_code == 204
    assert (await client.get(url, headers=auth)).status_code == 404
    assert (await client.delete(url, headers=auth)).status_code == 404


async def test_rss_feed_lists_published_posts(client, make_post):
    await make_post(title="Tom & Jerry <script>", summary="Escaped properly")
    await make_post(title="Hidden draft", published=False)

    response = await client.get("/api/feed.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/rss+xml")
    assert "Tom &amp; Jerry &lt;script&gt;" in response.text
    assert "/blog/tom-jerry-script" in response.text
    assert "Hidden draft" not in response.text
