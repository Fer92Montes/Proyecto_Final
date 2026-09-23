"""Vistas de la aplicación de tienda."""

from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView

from .models import Producto


class VistaTienda(TemplateView):
    """Muestra los productos más recientes en la página inicial de la tienda."""

    template_name = 'shop_abrazapinos/home.html'

    def get_context_data(self, **kwargs):
        """Añade los productos destacados a la vista."""
        contexto = super().get_context_data(**kwargs)
        contexto['products'] = Producto.objects.order_by('-created_at')[:6]
        return contexto


class VistaDetalleProducto(TemplateView):
    """Muestra el detalle completo de un producto de la tienda."""

    template_name = 'shop_abrazapinos/product_detail.html'

    def get_context_data(self, **kwargs):
        """Añade el producto actual y su información completa al contexto."""
        contexto = super().get_context_data(**kwargs)
        contexto['product'] = get_object_or_404(Producto, pk=self.kwargs.get('pk'))
        return contexto


def inicio(request):
    """Mantiene una vista funcional con el nombre más claro del proyecto."""
    return VistaTienda.as_view()(request)


home = inicio

__all__ = ['VistaTienda', 'VistaDetalleProducto', 'inicio', 'home']
