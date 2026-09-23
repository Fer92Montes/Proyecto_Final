"""Rutas principales del proyecto Django."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Redirige la raíz del dominio a la sección social por defecto.
    path('', RedirectView.as_view(url='/social/'), name='home'),
    # Ruta del panel de administración de Django.
    path('admin/', admin.site.urls),
    # Incluye todas las rutas de la parte social de la web.
    path('social/', include('social_abrazapinos.urls')),
    # Incluye todas las rutas de la sección de compraventa.
    path('shop/', include('shop_abrazapinos.urls')),
]
