"""Configuración WSGI del proyecto."""

import os

from django.core.wsgi import get_wsgi_application

# Establece la configuración del proyecto para que Django pueda iniciar el servidor
# WSGI con los ajustes definidos en config/settings.py.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
