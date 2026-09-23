"""Vistas de la aplicación social."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from .forms import (
    FormularioCambioContrasena,
    FormularioPerfil,
    FormularioPublicacion,
)
from .mixins import MixinContextoPerfil, MixinRequiereAutenticacion
from .models import Friendship
from .services import ServicioSocial


class VistaInicioSocial(TemplateView):
    """Muestra el feed principal de la red social."""

    template_name = 'social_abrazapinos/home.html'

    def get_context_data(self, **kwargs):
        """Añade las publicaciones visibles a la plantilla del inicio."""
        contexto = super().get_context_data(**kwargs)
        contexto['posts'] = ServicioSocial.obtener_publicaciones_visibles(self.request.user)
        return contexto


class VistaPerfilUsuario(MixinRequiereAutenticacion, MixinContextoPerfil, TemplateView):
    """Vista privada del perfil del usuario autenticado."""

    template_name = 'social_abrazapinos/profile.html'

    def get_context_data(self, **kwargs):
        """Crea el contexto del perfil personal con amigos y publicaciones."""
        contexto = super().get_context_data(**kwargs)
        contexto.update(self.obtener_contexto_perfil(self.request.user, self.request.user))
        return contexto


class VistaEditarPerfil(MixinRequiereAutenticacion, View):
    """Permite editar los datos del perfil y cambiar la contraseña."""

    template_name = 'social_abrazapinos/edit_profile.html'

    def get(self, request, *args, **kwargs):
        """Renderiza el formulario de edición con los datos actuales del usuario."""
        perfil = ServicioSocial.obtener_perfil_usuario(request.user)
        formulario_perfil = FormularioPerfil(instance=perfil)
        formulario_contraseña = FormularioCambioContrasena(request.user)
        return render(request, self.template_name, {
            'profile_form': formulario_perfil,
            'password_form': formulario_contraseña,
            'profile': perfil,
        })

    def post(self, request, *args, **kwargs):
        """Procesa la actualización del perfil o del cambio de contraseña."""
        perfil = ServicioSocial.obtener_perfil_usuario(request.user)
        formulario_perfil = FormularioPerfil(request.POST or None, instance=perfil)
        formulario_contraseña = FormularioCambioContrasena(request.user, request.POST or None)

        if 'profile_submit' in request.POST and formulario_perfil.is_valid():
            formulario_perfil.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('profile')

        if 'password_submit' in request.POST and formulario_contraseña.is_valid():
            formulario_contraseña.save()
            messages.success(request, 'Contraseña cambiada correctamente.')
            return redirect('profile')

        return render(request, self.template_name, {
            'profile_form': formulario_perfil,
            'password_form': formulario_contraseña,
            'profile': perfil,
        })


class VistaCrearPublicacion(MixinRequiereAutenticacion, View):
    """Crea nuevas publicaciones con visibilidad configurable."""

    template_name = 'social_abrazapinos/post_form.html'

    def get(self, request, *args, **kwargs):
        """Muestra el formulario del post en blanco."""
        return render(request, self.template_name, {'form': FormularioPublicacion()})

    def post(self, request, *args, **kwargs):
        """Guarda la publicación del usuario autenticado."""
        formulario = FormularioPublicacion(request.POST)
        if formulario.is_valid():
            publicacion = formulario.save(commit=False)
            publicacion.author = request.user
            publicacion.save()
            messages.success(request, 'Publicación creada correctamente.')
            return redirect('social_home')
        return render(request, self.template_name, {'form': formulario})


class VistaPerfilAjeno(View):
    """Muestra el perfil público de un usuario con sus publicaciones visibles."""

    template_name = 'social_abrazapinos/user_profile.html'

    def get(self, request, username, *args, **kwargs):
        """Obtiene el usuario visitado y prepara el contexto de la vista."""
        usuario_visitado = get_object_or_404(User, username=username)
        perfil = ServicioSocial.obtener_perfil_usuario(usuario_visitado)
        visitante = request.user if request.user.is_authenticated else None
        publicaciones = ServicioSocial.obtener_publicaciones_usuario(usuario_visitado, visitante)
        es_amigo = False

        if request.user.is_authenticated and request.user != usuario_visitado:
            es_amigo = Friendship.are_friends(request.user, usuario_visitado)

        contexto = {
            'profile_user': usuario_visitado,
            'profile': perfil,
            'friends': perfil.friends(),
            'posts': publicaciones,
            'is_friend': es_amigo,
        }
        return render(request, self.template_name, contexto)


class VistaAgregarAmigo(MixinRequiereAutenticacion, View):
    """Añade a un usuario a la lista de amigos del perfil actual."""

    def get(self, request, username, *args, **kwargs):
        """Mantiene la compatibilidad con la antigua navegación por GET."""
        return self._agregar_amigo(request, username)

    def post(self, request, username, *args, **kwargs):
        """Crea la relación de amistad de forma idempotente."""
        return self._agregar_amigo(request, username)

    def _agregar_amigo(self, request, username):
        """Lógica compartida para añadir un amigo y redirigir al perfil visitado."""
        usuario_objetivo = get_object_or_404(User, username=username)

        if request.user == usuario_objetivo:
            messages.info(request, 'No puedes agregarte a ti mismo como amigo.')
            return redirect('user_profile', username=username)

        Friendship.objects.get_or_create(from_user=request.user, to_user=usuario_objetivo)
        messages.success(request, f'Has añadido a {usuario_objetivo.username} a tu lista de amigos.')
        return redirect('user_profile', username=username)


class VistaIniciarSesion(View):
    """Inicia la sesión del usuario con Django auth."""

    template_name = 'social_abrazapinos/login.html'

    def get(self, request, *args, **kwargs):
        """Muestra el formulario de login si el usuario no está autenticado."""
        if request.user.is_authenticated:
            return redirect('social_home')
        return render(request, self.template_name, {'form': AuthenticationForm()})

    def post(self, request, *args, **kwargs):
        """Valida las credenciales y redirige al perfil si todo es correcto."""
        if request.user.is_authenticated:
            return redirect('social_home')

        formulario = AuthenticationForm(request, data=request.POST)
        if formulario.is_valid():
            login(request, formulario.get_user())
            return redirect('profile')
        return render(request, self.template_name, {'form': formulario})


class VistaCerrarSesion(View):
    """Cierra la sesión del usuario y devuelve al feed principal."""

    def get(self, request, *args, **kwargs):
        """Cierra la sesión y avisa al usuario del resultado."""
        logout(request)
        messages.info(request, 'Has cerrado sesión correctamente.')
        return redirect('social_home')


class VistaRegistro(View):
    """Registra nuevos usuarios y genera automáticamente su perfil."""

    template_name = 'social_abrazapinos/register.html'

    def get(self, request, *args, **kwargs):
        """Muestra el formulario de alta de usuario."""
        if request.user.is_authenticated:
            return redirect('social_home')
        return render(request, self.template_name, {'form': UserCreationForm()})

    def post(self, request, *args, **kwargs):
        """Guarda el usuario nuevo y redirige a su perfil privado."""
        if request.user.is_authenticated:
            return redirect('social_home')

        formulario = UserCreationForm(request.POST)
        if formulario.is_valid():
            usuario = formulario.save()
            ServicioSocial.obtener_perfil_usuario(usuario)
            login(request, usuario)
            messages.success(request, 'Usuario registrado con éxito.')
            return redirect('profile')
        return render(request, self.template_name, {'form': formulario})


# Alias funcional para mantener compatibilidad con el resto del proyecto.
SocialHomeView = VistaInicioSocial
ProfileView = VistaPerfilUsuario
EditProfileView = VistaEditarPerfil
CreatePostView = VistaCrearPublicacion
UserProfileView = VistaPerfilAjeno
AddFriendView = VistaAgregarAmigo
LoginView = VistaIniciarSesion
LogoutView = VistaCerrarSesion
RegisterView = VistaRegistro


def inicio(request):
    """Mantiene la vista principal con nombre en español para uso interno."""
    return VistaInicioSocial.as_view()(request)


def vista_perfil(request):
    """Mantiene la vista de perfil para compatibilidad con llamadas directas."""
    return VistaPerfilUsuario.as_view()(request)


def vista_editar_perfil(request):
    """Mantiene la edición de perfil para compatibilidad con llamadas directas."""
    return VistaEditarPerfil.as_view()(request)


def vista_crear_publicacion(request):
    """Mantiene la creación de posts para compatibilidad con llamadas directas."""
    return VistaCrearPublicacion.as_view()(request)


def vista_perfil_ajeno(request, username):
    """Mantiene la vista de perfil ajeno para compatibilidad con llamadas directas."""
    return VistaPerfilAjeno.as_view()(request, username=username)


def vista_agregar_amigo(request, username):
    """Mantiene la lógica de añadir amigos para compatibilidad con llamadas directas."""
    return VistaAgregarAmigo.as_view()(request, username=username)


def vista_iniciar_sesion(request):
    """Mantiene el login para compatibilidad con llamadas directas."""
    return VistaIniciarSesion.as_view()(request)


def vista_cerrar_sesion(request):
    """Mantiene cierre de sesión para compatibilidad con llamadas directas."""
    return VistaCerrarSesion.as_view()(request)


def vista_registro(request):
    """Mantiene el registro para compatibilidad con llamadas directas."""
    return VistaRegistro.as_view()(request)


# Alias históricos para no romper llamadas antiguas en el proyecto.
home = inicio
profile_view = vista_perfil
edit_profile_view = vista_editar_perfil
create_post_view = vista_crear_publicacion
user_profile_view = vista_perfil_ajeno
add_friend_view = vista_agregar_amigo
login_view = vista_iniciar_sesion
logout_view = vista_cerrar_sesion
register_view = vista_registro
