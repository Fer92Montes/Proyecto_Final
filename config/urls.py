"""Rutas principales del proyecto Django."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/social/'), name='home'),
    path('admin/', admin.site.urls),
    path('social/', include('social_abrazapinos.urls')),
    path('shop/', include('shop_abrazapinos.urls')),
]
