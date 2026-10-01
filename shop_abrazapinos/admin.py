"""Configuración del panel de administración de la tienda."""

from django.contrib import admin

from .models import LineaPedido, Pedido, Producto


@admin.register(Producto)
class AdminProducto(admin.ModelAdmin):
    """Permite gestionar los productos desde el panel de administración."""

    list_display = ('name', 'price', 'stock', 'created_at')
    search_fields = ('name', 'description')


ProductAdmin = AdminProducto


# El inline permite consultar los productos de un pedido sin abandonar su ficha.
class LineaPedidoInline(admin.TabularInline):
    """Muestra las líneas de cada pedido en su ficha de administración."""

    model = LineaPedido
    extra = 0
    readonly_fields = ('producto', 'nombre_producto', 'precio_unitario', 'cantidad')


@admin.register(Pedido)
class AdminPedido(admin.ModelAdmin):
    """Permite revisar pedidos y actualizar su estado desde el admin."""

    # Las columnas, filtros y búsqueda facilitan localizar pedidos y seguir su estado.
    list_display = ('id', 'usuario', 'destinatario', 'total', 'metodo_pago', 'estado', 'creado_en')
    list_filter = ('estado', 'metodo_pago', 'creado_en')
    search_fields = ('destinatario', 'usuario__username', 'codigo_postal')
    # El identificador permite localizar la sesión de Checkout en el panel de Stripe.
    readonly_fields = ('usuario', 'total', 'stripe_session_id', 'creado_en')
    inlines = (LineaPedidoInline,)
