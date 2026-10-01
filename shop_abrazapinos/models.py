"""Modelos de la aplicación de tienda."""

from django.conf import settings
from django.db import models


class Producto(models.Model):
    """Representa un producto disponible en la sección de compraventa."""

    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configuración de ordenación del modelo."""

        ordering = ['-created_at']

    def __str__(self):
        """Devuelve el nombre del producto como representación textual."""
        return self.name


# El pedido agrupa datos del cliente, entrega, estado y total calculado al confirmar.
class Pedido(models.Model):
    """Guarda los datos de entrega y pago preferido de un pedido confirmado."""

    # El cobro se realiza en Stripe Checkout; no se guardan datos de tarjeta localmente.
    # Las claves se almacenan en la base; las etiquetas son las que ve el usuario.
    METODOS_PAGO = [
        ('stripe', 'Stripe'),
    ]
    # El estado permite gestionar la preparación desde el panel de administración.
    ESTADOS = [
        ('pendiente_pago', 'Pendiente de pago'),
        ('pagado', 'Pagado'),
        ('pendiente', 'Pendiente'),
        ('preparando', 'En preparación'),
        ('enviado', 'Enviado'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    # PROTECT conserva la trazabilidad del pedido aunque se intente borrar su cuenta.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pedidos_tienda',
    )
    destinatario = models.CharField(max_length=120)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=120)
    # El valor vacío solo facilita migrar pedidos históricos; el formulario lo exige.
    provincia = models.CharField(max_length=120, default='')
    codigo_postal = models.CharField(max_length=20)
    pais = models.CharField(max_length=80, default='España')
    telefono = models.CharField(max_length=30, blank=True)
    metodo_pago = models.CharField(max_length=24, choices=METODOS_PAGO)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    # Permite relacionar webhook y regreso del navegador con una sesión de Stripe concreta.
    stripe_session_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f'Pedido #{self.pk} de {self.destinatario}'


# Cada línea congela el nombre y precio aplicados para que cambios futuros del catálogo
# no modifiquen el importe de un pedido ya registrado.
class LineaPedido(models.Model):
    """Conserva cantidad, nombre y precio del producto al confirmar la compra."""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    nombre_producto = models.CharField(max_length=200)
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    cantidad = models.PositiveIntegerField()

    @property
    def subtotal(self):
        """Calcula el importe de la línea usando su precio histórico."""
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f'{self.cantidad} × {self.nombre_producto}'


Product = Producto
