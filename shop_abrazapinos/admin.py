"""Configuración del panel de administración de la tienda."""

from django.contrib import admin

from .models import Producto


@admin.register(Producto)
class AdminProducto(admin.ModelAdmin):
    """Permite gestionar los productos desde el panel de administración."""

    list_display = ('name', 'price', 'stock', 'created_at')
    search_fields = ('name', 'description')


ProductAdmin = AdminProducto
