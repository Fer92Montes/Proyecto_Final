"""Rutas principales del proyecto Django."""

from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path


def landing_page(request):
    """Renderiza la portada principal del club con acceso directo a social y tienda."""
    return render(request, 'landing.html')


urlpatterns = [
    # Portada principal del club con enlaces directos a social y compraventa.
    path('', landing_page, name='home'),
    # Ruta del panel de administración de Django.
    path('admin/', admin.site.urls),
    # Incluye todas las rutas de la parte social de la web.
    path('social/', include('social_abrazapinos.urls')),
    # Incluye todas las rutas de la sección de compraventa.
    path('shop/', include('shop_abrazapinos.urls')),
]
