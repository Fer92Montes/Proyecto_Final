"""Modelos de la aplicación social."""

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q


class Profile(models.Model):
    """Añade información adicional del usuario dentro de la red social."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    instagram = models.CharField(max_length=100, blank=True, default='')
    strava = models.URLField(blank=True, default='')
    bike_model = models.CharField(max_length=150, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena los perfiles por fecha de creación descendente."""

        ordering = ['-created_at']

    def __str__(self):
        """Devuelve el nombre de usuario para identificar el perfil."""
        return f'Perfil de {self.user.username}'

    @property
    def display_name(self):
        """Devuelve el nombre completo si existe; si no, el usuario."""
        full_name = ' '.join(part for part in (self.user.first_name, self.user.last_name) if part).strip()
        return full_name or self.user.username

    def friends(self):
        """Obtiene los usuarios que siguen a este perfil."""
        return User.objects.filter(
            Q(friendships_from__to_user=self.user) | Q(friendships_to__from_user=self.user)
        ).distinct()


class Friendship(models.Model):
    """Relación de amistad entre usuarios."""

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_from')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_to')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['from_user', 'to_user'], name='unique_friendship'),
        ]
        ordering = ['-created_at']

    @staticmethod
    def are_friends(user_a, user_b):
        """Comprueba si dos usuarios son amigos."""
        if user_a is None or user_b is None or user_a == user_b:
            return True
        return Friendship.objects.filter(
            Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a)
        ).exists()

    def __str__(self):
        return f'{self.from_user} -> {self.to_user}'


class Post(models.Model):
    """Representa una publicación del feed social."""

    VISIBILITY_CHOICES = [
        ('public', 'Todos los usuarios'),
        ('friends', 'Solo amigos'),
        ('private', 'Solo yo'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena las publicaciones por fecha de creación descendente."""

        ordering = ['-created_at']

    def is_visible_to(self, viewer):
        """Determina si un usuario puede ver la publicación."""
        if self.author == viewer:
            return True
        if self.visibility == 'public':
            return True
        if self.visibility == 'friends':
            if viewer is None or not getattr(viewer, 'is_authenticated', False):
                return False
            return Friendship.are_friends(self.author, viewer)
        return False

    def __str__(self):
        """Devuelve el título de la publicación como representación textual."""
        return self.title
