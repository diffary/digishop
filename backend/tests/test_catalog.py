async def test_list_products_excludes_inactive(client, sample_data):
    r = await client.get("/products")
    assert r.status_code == 200
    slugs = [p["slug"] for p in r.json()]
    assert sorted(slugs) == ["pixel-ui-kit", "tank-pack-3d"]


async def test_filter_by_category(client, sample_data):
    r = await client.get("/products", params={"category": "game-assets"})
    assert r.status_code == 200
    assert len(r.json()) == 2
    r = await client.get("/products", params={"category": "templates"})
    assert r.json() == []


async def test_search_by_name(client, sample_data):
    r = await client.get("/products", params={"search": "tank"})
    assert [p["slug"] for p in r.json()] == ["tank-pack-3d"]


async def test_product_detail_by_slug(client, sample_data):
    r = await client.get("/products/tank-pack-3d")
    assert r.status_code == 200
    body = r.json()
    assert body["price"] == 1999
    assert "file_key" not in body  # путь к файлу наружу не отдаём


async def test_product_detail_404(client):
    r = await client.get("/products/no-such")
    assert r.status_code == 404


async def test_inactive_product_detail_404(client, sample_data):
    r = await client.get("/products/old-bundle")
    assert r.status_code == 404


async def test_list_categories(client, sample_data):
    r = await client.get("/categories")
    assert sorted(c["slug"] for c in r.json()) == ["game-assets", "templates"]
