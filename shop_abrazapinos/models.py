"""Modelos de la aplicación de tienda."""

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


Product = Producto
