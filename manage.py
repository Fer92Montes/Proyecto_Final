#!/usr/bin/env python
"""Utilidad de gestión de Django para tareas administrativas."""
import os
import sys


def main():
    """Ejecuta las tareas administrativas de Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Estás seguro de que está instalado y "
            "disponible en la variable de entorno PYTHONPATH? ¿Olvidaste "
            "activar el entorno virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
