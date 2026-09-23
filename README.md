# Abrazapinos

Proyecto final desarrollado con Django para una comunidad de ciclismo de montaña y actividades sociales. La aplicación combina una red social con una sección de compraventa, permitiendo a los usuarios interactuar, compartir publicaciones y explorar productos.

## Objetivo
Crear una plataforma web para una comunidad de bikers donde puedan:
- registrarse e iniciar sesión
- crear y visualizar publicaciones
- gestionar su perfil
- añadir amigos
- publicar productos en una tienda
- navegar por detalles de publicaciones y productos

## Funcionalidades principales

### Social
- Registro e inicio de sesión
- Perfil privado para usuarios autenticados
- Edición del perfil desde la propia web
- Gestión de amistades
- Feed con publicaciones públicas, de amigos y privadas
- Creación, edición y eliminación de publicaciones
- Vista detallada de cada publicación
- Perfil público de otros usuarios con enlaces directos

### Tienda
- Catálogo de productos
- Detalle individual por producto
- Información de precio, stock y descripción

### UX y diseño
- Tema claro y oscuro gestionado con JavaScript en los templates
- Menú de navegación consistente
- Diseño adaptado a la identidad de la aplicación

## Tecnologías utilizadas
- Python
- Django
- SQLite
- HTML5
- CSS3
- JavaScript embebido en templates de Django

## Estructura del proyecto

- config/: configuración principal del proyecto Django
- social_abrazapinos/: aplicación de red social
- shop_abrazapinos/: aplicación de compraventa
- manage.py: punto de entrada del proyecto

## Requisitos
- Python 3.10 o superior
- pip
- virtualenv o venv

## Instalación y ejecución

1. Clona el repositorio y entra en la carpeta del proyecto.
2. Crea un entorno virtual:
   python -m venv .venv
3. Activa el entorno virtual:
   - Windows: .\.venv\Scripts\activate
   - Linux/macOS: source .venv/bin/activate
4. Instala las dependencias:
   pip install -r requirements.txt
5. Ejecuta las migraciones:
   python manage.py migrate
6. Inicia el servidor:
   python manage.py runserver
7. Abre la aplicación en el navegador en:
   http://127.0.0.1:8000/

La ruta raíz redirige a la parte social por defecto.

## Acceso administrativo
Para crear un superusuario:

python manage.py createsuperuser

Tras eso puedes acceder a:
- /admin/

## Credenciales de ejemplo
Si se crea un superusuario con Django, se puede acceder al panel de administración desde la URL indicada.

## Autor
- Fernando Montes Mancebo

## Fecha
2026