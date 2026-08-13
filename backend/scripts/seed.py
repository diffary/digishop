"""Idempotent demo-data seeder for DigiShop.

Run with: uv run python -m scripts.seed
"""

import asyncio

from sqlalchemy import select

from app.core.db import session_factory
from app.models import Category, Product

CATEGORIES = [
    {"name": "Игровые ассеты", "slug": "game-assets"},
    {"name": "Шаблоны", "slug": "templates"},
    {"name": "Пресеты", "slug": "presets"},
]

PRODUCTS = [
    # game-assets
    {
        "category_slug": "game-assets",
        "name": "Tank Pack 3D",
        "slug": "tank-pack-3d",
        "description": "Набор 3D-моделей танков для игр",
        "price": 1999,
    },
    {
        "category_slug": "game-assets",
        "name": "Pixel UI Kit",
        "slug": "pixel-ui-kit",
        "description": "Пиксельный набор UI для игр",
        "price": 999,
    },
    {
        "category_slug": "game-assets",
        "name": "Fantasy Characters Pack",
        "slug": "fantasy-characters-pack",
        "description": "Набор фэнтезийных персонажей",
        "price": 2999,
    },
    # templates
    {
        "category_slug": "templates",
        "name": "Landing Page Template",
        "slug": "landing-page-template",
        "description": "Шаблон лендинга для digital-товаров",
        "price": 1499,
    },
    {
        "category_slug": "templates",
        "name": "Portfolio Template",
        "slug": "portfolio-template",
        "description": "Шаблон портфолио разработчика",
        "price": 1299,
    },
    {
        "category_slug": "templates",
        "name": "Admin Dashboard Template",
        "slug": "admin-dashboard-template",
        "description": "Шаблон административной панели",
        "price": 4999,
    },
    # presets
    {
        "category_slug": "presets",
        "name": "Cinematic LUT Pack",
        "slug": "cinematic-lut-pack",
        "description": "Набор LUT-пресетов для видео",
        "price": 799,
    },
    {
        "category_slug": "presets",
        "name": "Lightroom Presets Pack",
        "slug": "lightroom-presets-pack",
        "description": "Набор пресетов Lightroom",
        "price": 499,
    },
    {
        "category_slug": "presets",
        "name": "Photoshop Actions Pack",
        "slug": "photoshop-actions-pack",
        "description": "Набор экшенов Photoshop",
        "price": 899,
    },
]


async def main() -> None:
    factory = session_factory()
    async with factory() as session:
        slug_to_id: dict[str, int] = {}

        for cat in CATEGORIES:
            existing = await session.scalar(
                select(Category).where(Category.slug == cat["slug"])
            )
            if existing is not None:
                print(f"category skipped (exists): {cat['slug']}")
                slug_to_id[cat["slug"]] = existing.id
                continue
            category = Category(name=cat["name"], slug=cat["slug"])
            session.add(category)
            await session.flush()
            slug_to_id[cat["slug"]] = category.id
            print(f"category created: {cat['slug']}")

        for prod in PRODUCTS:
            existing = await session.scalar(
                select(Product).where(Product.slug == prod["slug"])
            )
            if existing is not None:
                print(f"product skipped (exists): {prod['slug']}")
                continue
            product = Product(
                category_id=slug_to_id[prod["category_slug"]],
                name=prod["name"],
                slug=prod["slug"],
                description=prod["description"],
                price=prod["price"],
                image_url=None,
                file_key=f"files/{prod['slug']}.zip",
                is_active=True,
            )
            session.add(product)
            print(f"product created: {prod['slug']}")

        await session.commit()

    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
