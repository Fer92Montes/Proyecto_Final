"""Rutas de la aplicación de tienda."""

from django.urls import path

from . import views

# La tienda expone una página principal con productos y una vista detalle por ID.
urlpatterns = [
    path('', views.inicio, name='shop_home'),
    path('productos/<int:pk>/', views.VistaDetalleProducto.as_view(), name='detalle_producto'),
]
