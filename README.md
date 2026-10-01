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
- Carrito de compra con edición de cantidades y validación de existencias
- Checkout alojado de Stripe para pagos con tarjeta
- Pedidos confirmados mediante webhook firmado de Stripe

### Pago con Stripe
La aplicación usa Stripe Checkout en modo de pruebas. El servidor crea la sesión con precios consultados desde la base de datos, reserva el stock durante 35 minutos y confirma el pedido únicamente cuando Stripe informa del pago. Los datos de tarjeta se introducen en Stripe y no se guardan en este proyecto.

La configuración local se carga desde `.env`, situado junto a `manage.py`. Ese archivo está excluido de Git; no añadas claves reales ni de prueba al repositorio.

En Windows, instala también Stripe CLI (es una herramienta aparte del paquete Python) y abre una terminal nueva para actualizar el `PATH`:

```powershell
winget install --id Stripe.StripeCli --exact --source winget
stripe version
stripe login
```

Aprueba el acceso desde el navegador cuando Stripe CLI lo solicite.

Desde la raíz del proyecto, crea el archivo local a partir de la plantilla:

```powershell
Copy-Item .env.example .env
```

Edita `.env` y sustituye los marcadores por tu clave secreta de pruebas `sk_test_...` y por el secreto `whsec_...` que imprime Stripe CLI. La moneda puede quedarse como `eur`. Después inicia Django normalmente:

Obtén `STRIPE_SECRET_KEY` desde el panel de Stripe en modo de pruebas. Para recibir y validar eventos localmente, inicia Stripe CLI en otra terminal:

Usa el secreto `whsec_...` que imprime Stripe CLI como `STRIPE_WEBHOOK_SECRET` en `.env`. El endpoint procesa `checkout.session.completed`, `checkout.session.expired` y eventos de pago asíncrono; las firmas se verifican con el cuerpo original de la petición.

```powershell
stripe listen --events checkout.session.completed,checkout.session.expired,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed --forward-to http://localhost:8000/shop/stripe/webhook/
```
No Debes cerrar este powershell mientras quieras utilizar la clave `wshec_...`

```powershell
python manage.py runserver
```

Para simular una compra aprobada en Checkout, usa la tarjeta de prueba `4242 4242 4242 4242`, una fecha futura y cualquier CVC. No uses datos de tarjeta reales mientras trabajes en modo de prueba.

### UX y diseño
- Tema claro y oscuro gestionado con JavaScript en los templates
- Menú de navegación consistente
- Diseño adaptado a la identidad de la aplicación

## Tecnologías utilizadas
- Python
- Django
- Stripe Python SDK
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