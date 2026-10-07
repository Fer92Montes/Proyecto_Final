"""Modelos de la aplicación social."""

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.core.files.storage import default_storage


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
        # Se construye el nombre visible a partir de nombre + apellidos para mostrar
        # un perfil más amigable en la interfaz sin perder el username como fallback.
        full_name = ' '.join(part for part in (self.user.first_name, self.user.last_name) if part).strip()
        return full_name or self.user.username

    def friends(self):
        """Obtiene los usuarios que siguen a este perfil."""
        # Usa una consulta OR sobre ambas relaciones de amistad para incluir tanto
        # usuarios que siguen al perfil como usuarios a los que sigue el perfil.
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
        # Si el usuario no existe o es el mismo usuario, se considera válido para
        # evitar bloqueos innecesarios en vistas de perfil y publicaciones.
        if user_a is None or user_b is None or user_a == user_b:
            return True
        # La relación es no dirigida: se comprueba en ambas direcciones para que
        # la amistad sea simétrica independentemente de quién la creó.
        return Friendship.objects.filter(
            Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a)
        ).exists()

    def __str__(self):
        return f'{self.from_user} -> {self.to_user}'


class Post(models.Model):
    """Publicación social con imagen, visibilidad del autor y moderación administrativa.

    `is_hidden` es una suspensión reversible que prevalece sobre la visibilidad
    elegida por el autor; la imagen puede omitirse y se guarda bajo MEDIA_ROOT.
    """

    VISIBILITY_CHOICES = [
        ('public', 'Todos los usuarios'),
        ('friends', 'Solo amigos'),
        ('private', 'Solo yo'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    # Archivo opcional adjunto al post; los signals gestionan reemplazos y borrados.
    image = models.ImageField(upload_to='publicaciones/', blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    # Moderación reversible: al activarse, prevalece sobre la visibilidad del autor.
    is_hidden = models.BooleanField(default=False, verbose_name='Oculta por moderación')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Ordena las publicaciones por fecha de creación descendente."""

        ordering = ['-created_at']

    def is_visible_to(self, viewer):
        """Determina si un usuario puede ver la publicación."""
        if self.is_hidden:
            return False
        # El autor siempre puede ver su propia publicación, aunque sea privada.
        if self.author == viewer:
            return True
        if self.visibility == 'public':
            return True
        if self.visibility == 'friends':
            # Las publicaciones de amigos solo son visibles para usuarios autenticados
            # que realmente tengan una relación de amistad con el autor.
            if viewer is None or not getattr(viewer, 'is_authenticated', False):
                return False
            return Friendship.are_friends(self.author, viewer)
        # En el caso de 'private', solo el autor tiene acceso.
        return False

    def __str__(self):
        """Devuelve el título de la publicación como representación textual."""
        return self.title


@receiver(pre_save, sender=Post)
def recordar_imagen_anterior_publicacion(sender, instance, **kwargs):
    """Recuerda el archivo previo durante el guardado para evitar huérfanos.

    La consulta solo obtiene el nombre almacenado; el borrado se difiere a
    `post_save` para no perder la imagen si falla la validación o el guardado.
    """
    if not instance.pk:
        instance._imagen_anterior = ''
        return
    instance._imagen_anterior = (
        Post.objects.filter(pk=instance.pk).values_list('image', flat=True).first() or ''
    )


@receiver(post_save, sender=Post)
def limpiar_imagen_reemplazada_publicacion(sender, instance, **kwargs):
    """Elimina del storage la imagen sustituida o quitada tras guardar el post."""
    anterior = getattr(instance, '_imagen_anterior', '')
    actual = instance.image.name if instance.image else ''
    if anterior and anterior != actual:
        default_storage.delete(anterior)


@receiver(post_delete, sender=Post)
def limpiar_imagen_eliminada_publicacion(sender, instance, **kwargs):
    """Elimina del storage el archivo asociado al borrar definitivamente el post."""
    if instance.image:
        default_storage.delete(instance.image.name)
