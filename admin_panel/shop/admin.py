from django.contrib import admin

from shop.models import Category, Product, ShopUser


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "price", "file_key", "is_active")
    list_filter = ("category",)
    search_fields = ("name", "slug")
    list_editable = ("price", "file_key", "is_active")


@admin.register(ShopUser)
class ShopUserAdmin(admin.ModelAdmin):
    list_display = ("email", "google_id", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


from shop.orders_admin import *
