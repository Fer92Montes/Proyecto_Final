"""Configuración de la aplicación de tienda."""

from django.apps import AppConfig


class ShopAbrazapinosConfig(AppConfig):
    """Configura la aplicación de compraventa de Abrazapinos."""

    # Identificador de la app en el proyecto para que Django pueda cargar sus
    # modelos, vistas y rutas correspondientes.
    name = 'shop_abrazapinos'
