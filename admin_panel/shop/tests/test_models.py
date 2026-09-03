from datetime import UTC, datetime

from django.test import TestCase

from shop.models import Category, DownloadLink, Order, OrderItem, Product, ShopUser


class UnmanagedModelContractTests(TestCase):
    """Fixes the managed=False contract: Django must never migrate the shop app."""

    def test_product_is_declared_unmanaged(self) -> None:
        self.assertFalse(Product._meta.managed)

    def test_db_table_names_match_alembic_schema(self) -> None:
        self.assertEqual(ShopUser._meta.db_table, "users")
        self.assertEqual(Category._meta.db_table, "categories")
        self.assertEqual(Product._meta.db_table, "products")
        self.assertEqual(Order._meta.db_table, "orders")
        self.assertEqual(OrderItem._meta.db_table, "order_items")
        self.assertEqual(DownloadLink._meta.db_table, "download_links")


class OrmRoundtripTests(TestCase):
    """Smoke test: the ORM can read/write the real tables through joins."""

    def setUp(self) -> None:
        self.user = ShopUser.objects.create(
            email="buyer@test.dev",
            password_hash="hash",
            created_at=datetime.now(UTC),
        )
        self.category = Category.objects.create(name="Игровые ассеты", slug="game-assets")
        self.product = Product.objects.create(
            category=self.category,
            name="Tank Pack 3D",
            slug="tank-pack-3d",
            description="3D tank models",
            price=1999,
            file_key="files/tank-pack-3d.zip",
            is_active=True,
        )
        self.order = Order.objects.create(
            user=self.user,
            status=Order.Status.PAID,
            total=1999,
            provider="stripe",
            created_at=datetime.now(UTC),
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price_at_purchase=1999,
        )
        self.download_link = DownloadLink.objects.create(
            order_item=self.order_item,
            token="a" * 36,
            expires_at=datetime.now(UTC),
            download_count=0,
        )

    def test_join_across_order_to_user_email(self) -> None:
        order = Order.objects.select_related("user").get(id=self.order.id)
        self.assertEqual(order.user.email, "buyer@test.dev")

    def test_join_across_product_to_category_name(self) -> None:
        product = Product.objects.select_related("category").get(id=self.product.id)
        self.assertEqual(product.category.name, "Игровые ассеты")

    def test_order_item_joins_order_and_product(self) -> None:
        item = OrderItem.objects.select_related("order", "product").get(id=self.order_item.id)
        self.assertEqual(item.order.id, self.order.id)
        self.assertEqual(item.product.slug, "tank-pack-3d")

    def test_download_link_joins_order_item(self) -> None:
        link = DownloadLink.objects.select_related("order_item").get(id=self.download_link.id)
        self.assertEqual(link.order_item.id, self.order_item.id)
