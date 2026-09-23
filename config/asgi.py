"""Configuración ASGI del proyecto."""

import os

from django.core.asgi import get_asgi_application

# Indica a Django qué módulo de configuración debe cargar al arrancar el servidor
# ASGI, permitiendo que la aplicación funcione en un entorno asíncrono.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
