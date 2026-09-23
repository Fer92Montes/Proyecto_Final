"""Servicios reutilizables para la lógica social de la aplicación."""

from __future__ import annotations

from typing import Iterable

from django.contrib.auth.models import User
from django.db.models import Q

from .models import Post, Profile


class ServicioSocial:
    """Centraliza la lógica compartida de perfiles, amistades y publicaciones."""

    @staticmethod
    def obtener_perfil_usuario(usuario: User) -> Profile:
        """Devuelve el perfil del usuario, creándolo si aún no existe."""
        # Se usa get_or_create para asegurar que cualquier usuario autenticado tenga
        # un perfil asociado aunque no haya completado aún su registro social.
        return Profile.objects.get_or_create(user=usuario)[0]

    @staticmethod
    def obtener_amigos_usuario(usuario: User):
        """Obtiene los usuarios que forman parte de la red de amigos del usuario."""
        # Si el usuario no está autenticado no tiene red de amistades consultable.
        if usuario is None or not getattr(usuario, 'is_authenticated', False):
            return User.objects.none()
        # La relación se busca desde ambos lados para aceptar amistades creadas en
        # cualquiera de las dos direcciones de la relación.
        return User.objects.filter(
            Q(friendships_from__to_user=usuario) | Q(friendships_to__from_user=usuario)
        ).distinct()

    @staticmethod
    def obtener_publicaciones_visibles(usuario: User | None):
        """Devuelve las publicaciones visibles para un usuario concreto."""
        # Los visitantes anónimos solo pueden ver publicaciones públicas.
        if usuario is None or not getattr(usuario, 'is_authenticated', False):
            return Post.objects.filter(visibility='public').order_by('-created_at')

        amigos = ServicioSocial.obtener_amigos_usuario(usuario)
        # El feed combina tres fuentes: publicaciones propias, públicas y de amigos.
        return Post.objects.filter(
            Q(author=usuario)
            | Q(visibility='public')
            | (Q(visibility='friends') & Q(author__in=amigos))
        ).distinct().order_by('-created_at')

    @staticmethod
    def obtener_publicaciones_usuario(usuario: User, visitante: User | None = None) -> Iterable[Post]:
        """Obtiene los posts del usuario filtrados según el usuario que los está viendo."""
        # Se consulta el conjunto de publicaciones del autor y luego se filtra con la
        # lógica de visibilidad de cada post según el visitante concreto.
        queryset = Post.objects.filter(author=usuario).order_by('-created_at')
        return [publicacion for publicacion in queryset if publicacion.is_visible_to(visitante)]

    # Alias de compatibilidad con nombres anteriores.
    obtener_perfil_para_usuario = obtener_perfil_usuario
    obtener_usuarios_amigos = obtener_amigos_usuario
    obtener_publicaciones_visibles_para_usuario = obtener_publicaciones_visibles
    obtener_publicaciones_de_usuario = obtener_publicaciones_usuario


# Alias de compatibilidad para evitar romper referencias antiguas.
SocialService = ServicioSocial

__all__ = ['ServicioSocial', 'SocialService']
