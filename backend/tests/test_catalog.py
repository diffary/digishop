import pytest

from app.models import Category, Product


@pytest.fixture
async def sample_data(db_session):
    game_assets = Category(name="Игровые ассеты", slug="game-assets")
    templates = Category(name="Шаблоны", slug="templates")
    db_session.add_all([game_assets, templates])
    await db_session.flush()

    products = [
        Product(
            category_id=game_assets.id,
            name="Tank Pack 3D",
            slug="tank-pack-3d",
            description="3D tank models",
            price=1999,
            image_url=None,
            file_key="files/tank-pack-3d.zip",
            is_active=True,
        ),
        Product(
            category_id=game_assets.id,
            name="Pixel UI Kit",
            slug="pixel-ui-kit",
            description="Pixel art UI kit",
            price=999,
            image_url=None,
            file_key="files/pixel-ui-kit.zip",
            is_active=True,
        ),
        Product(
            category_id=templates.id,
            name="Old Bundle",
            slug="old-bundle",
            description="Deprecated bundle",
            price=499,
            image_url=None,
            file_key="files/old-bundle.zip",
            is_active=False,
        ),
    ]
    db_session.add_all(products)
    await db_session.commit()


async def test_list_products_excludes_inactive(client, sample_data):
    r = await client.get("/products")
    assert r.status_code == 200
    slugs = [p["slug"] for p in r.json()]
    assert sorted(slugs) == ["pixel-ui-kit", "tank-pack-3d"]


async def test_filter_by_category(client, sample_data):
    r = await client.get("/products", params={"category": "game-assets"})
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
