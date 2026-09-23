"""Rutas de la aplicación de tienda."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.inicio, name='shop_home'),
]
