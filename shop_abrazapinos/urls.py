"""Rutas de la aplicación de tienda."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='shop_home'),
]
