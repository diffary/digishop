from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from shop.models import Category, Order, OrderItem, Product, ShopUser


class AdminTestsBase(TestCase):
    def setUp(self) -> None:
        self.superuser = get_user_model().objects.create_superuser(
            username="admin", email="admin@digishop.dev", password="password123"
        )
        self.client.force_login(self.superuser)

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
        self.shop_user = ShopUser.objects.create(
            email="buyer@test.dev",
            password_hash="hash",
            created_at=datetime.now(UTC),
        )
        self.order = Order.objects.create(
            user=self.shop_user,
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


class AdminIndexTests(AdminTestsBase):
    def test_admin_index_loads(self) -> None:
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)


class ProductAdminTests(AdminTestsBase):
    def test_changelist_filters_by_category(self) -> None:
        other_category = Category.objects.create(name="Музыка", slug="music")
        other_product = Product.objects.create(
            category=other_category,
            name="Loop Pack",
            slug="loop-pack",
            description="Audio loops",
            price=999,
            file_key="files/loop-pack.zip",
            is_active=True,
        )
        url = reverse("admin:shop_product_changelist")
        response = self.client.get(url, {"category__id__exact": self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)
        self.assertNotContains(response, other_product.name)

    def test_change_form_saves_new_file_key(self) -> None:
        url = reverse("admin:shop_product_change", args=[self.product.id])
        response = self.client.post(
            url,
            {
                "category": self.category.id,
                "name": self.product.name,
                "slug": self.product.slug,
                "description": self.product.description,
                "price": self.product.price,
                "image_url": "",
                "file_key": "files/tank-pack-3d-v2.zip",
                "is_active": "on",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.file_key, "files/tank-pack-3d-v2.zip")


class OrderAdminTests(AdminTestsBase):
    def test_changelist_shows_buyer_email(self) -> None:
        url = reverse("admin:shop_order_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "buyer@test.dev")

    def test_add_order_forbidden(self) -> None:
        url = reverse("admin:shop_order_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_delete_order_forbidden(self) -> None:
        url = reverse("admin:shop_order_delete", args=[self.order.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class ShopUserAdminTests(AdminTestsBase):
    def test_add_shop_user_forbidden(self) -> None:
        url = reverse("admin:shop_shopuser_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
