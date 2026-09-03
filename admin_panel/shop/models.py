from django.db import models

# All models below are managed=False: Django never creates, alters, or drops these
# tables. Alembic (backend/alembic/versions/) is the schema source of truth; the
# column definitions here are mirrored from edbcbe791bfa_initial_schema.py and
# ce202e1763ab_add_paid_at_to_orders.py and must be kept in sync by hand.
#
# notifications is intentionally not modeled here (see plan §Предпосылки: internal
# delivery log, no admin UI value).


class ShopUser(models.Model):
    """Store customers (backend `users` table) -- distinct from Django's own
    auth_user table, which holds admin-panel operators. A shop customer never
    appears as a Django admin login and vice versa."""

    email = models.CharField(max_length=320, unique=True)
    password_hash = models.CharField(max_length=128, null=True, blank=True)
    google_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "users"

    def __str__(self) -> str:
        return self.email


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, unique=True)

    class Meta:
        managed = False
        db_table = "categories"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.DO_NOTHING, db_column="category_id", related_name="products"
    )
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    price = models.IntegerField()
    image_url = models.CharField(max_length=500, null=True, blank=True)
    file_key = models.CharField(max_length=500)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "products"

    def __str__(self) -> str:
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        ShopUser, on_delete=models.DO_NOTHING, db_column="user_id", related_name="orders"
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    total = models.IntegerField()
    provider = models.CharField(max_length=20)
    payment_session_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "orders"

    def __str__(self) -> str:
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.DO_NOTHING, db_column="order_id", related_name="items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.DO_NOTHING, db_column="product_id", related_name="order_items"
    )
    price_at_purchase = models.IntegerField()

    class Meta:
        managed = False
        db_table = "order_items"

    def __str__(self) -> str:
        return f"OrderItem #{self.pk}"


class DownloadLink(models.Model):
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.DO_NOTHING,
        db_column="order_item_id",
        related_name="download_links",
    )
    token = models.CharField(max_length=36, unique=True)
    expires_at = models.DateTimeField()
    download_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = "download_links"

    def __str__(self) -> str:
        return self.token
