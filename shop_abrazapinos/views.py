"""Vistas de la aplicación de tienda."""

from django.shortcuts import render

from .models import Product


def home(request):
    """Muestra los productos más recientes en la página inicial de la tienda."""
    products = Product.objects.order_by('-created_at')[:6]
    return render(request, 'shop_abrazapinos/home.html', {'products': products})
