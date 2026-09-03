from typing import ClassVar

from django.contrib import admin

from shop.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "price_at_purchase")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user_email", "status", "total", "created_at")
    list_filter = ("status",)
    readonly_fields = (
        "user",
        "status",
        "total",
        "provider",
        "payment_session_id",
        "created_at",
        "paid_at",
    )
    inlines: ClassVar = [OrderItemInline]

    @admin.display(description="Buyer email")
    def user_email(self, obj):
        return obj.user.email

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
