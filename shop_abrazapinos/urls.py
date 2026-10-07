"""Rutas de la aplicación de tienda."""

from django.urls import path

from . import views

# El mapa separa navegación de catálogo, operaciones POST del carrito y el checkout.
# Los nombres permiten construir enlaces desde plantillas sin fijar rutas manualmente.
urlpatterns = [
    path('', views.inicio, name='shop_home'),
    # Gestión del catálogo en la web; cada operación exige su permiso add/change/delete.
    path('gestion/', views.VistaGestionProductos.as_view(), name='gestion_productos'),
    path('gestion/productos/nuevo/', views.crear_producto, name='crear_producto'),
    path('gestion/productos/<int:pk>/editar/', views.editar_producto, name='editar_producto'),
    path('gestion/productos/<int:pk>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/anadir/<int:pk>/', views.anadir_al_carrito, name='cart_add'),
    # Actualiza la cantidad de una línea; enviar cero elimina el producto de la sesión.
    path('carrito/actualizar/<int:pk>/', views.actualizar_cantidad_carrito, name='cart_update'),
    path('carrito/quitar/<int:pk>/', views.quitar_del_carrito, name='cart_remove'),
    path('tramitar-pedido/', views.tramitar_pedido, name='tramitar_pedido'),
    # Stripe Checkout se crea mediante POST; éxito y cancelación regresan a vistas autenticadas.
    path('tramitar-pedido/confirmar/', views.confirmar_pedido, name='confirmar_pedido'),
    path('pedido/<int:pk>/stripe/success/', views.stripe_success, name='stripe_success'),
    path('pedido/<int:pk>/stripe/cancel/', views.stripe_cancel, name='stripe_cancel'),
    # La firma del webhook se valida dentro de la vista usando el cuerpo HTTP original.
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('pedido/<int:pk>/confirmado/', views.pedido_confirmado, name='pedido_confirmado'),
    # Historial privado y detalle comprobado contra el propietario de cada pedido.
    path('pedidos/', views.historial_compras, name='historial_compras'),
    path('pedido/<int:pk>/', views.detalle_pedido, name='detalle_pedido'),
    path('productos/<int:pk>/', views.VistaDetalleProducto.as_view(), name='detalle_producto'),
]
