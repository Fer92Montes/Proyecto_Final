"""Mixins reutilizables para la lógica común de la aplicación social."""

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin


class MixinRequiereAutenticacion(LoginRequiredMixin):
    """Centraliza la configuración de las vistas protegidas por login."""

    login_url = '/social/login/'
    redirect_field_name = 'next'


class MixinContextoPerfil:
    """Proporciona contexto común para las vistas que muestran perfiles."""

    def obtener_contexto_perfil(self, usuario: Any, usuario_actual: Any = None) -> dict[str, Any]:
        """Devuelve el perfil, amigos y publicaciones visibles de un usuario."""
        from .services import ServicioSocial

        perfil = ServicioSocial.obtener_perfil_usuario(usuario)
        autor = usuario_actual if usuario_actual is not None else usuario
        return {
            'profile': perfil,
            'friends': perfil.friends(),
            'posts': ServicioSocial.obtener_publicaciones_usuario(usuario, autor),
        }


__all__ = ['MixinRequiereAutenticacion', 'MixinContextoPerfil']
