"""Modelos de la aplicación social."""

from django.contrib.auth.models import User
from django.db import models


class Post(models.Model):
    """Representa una publicación del feed social."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena las publicaciones por fecha de creación descendente."""

        ordering = ['-created_at']

    def __str__(self):
        """Devuelve el título de la publicación como representación textual."""
        return self.title


class Profile(models.Model):
    """Añade información adicional del usuario dentro de la red social."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena los perfiles por fecha de creación descendente."""

        ordering = ['-created_at']

    def __str__(self):
        """Devuelve el nombre de usuario para identificar el perfil."""
        return f'Perfil de {self.user.username}'
