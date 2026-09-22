"""Configuración del panel de administración de la tienda."""

from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Permite gestionar los productos desde el panel de administración."""

    list_display = ('name', 'price', 'stock', 'created_at')
    search_fields = ('name', 'description')
