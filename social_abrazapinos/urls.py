"""Rutas de la aplicación social."""

from django.urls import path

from . import views

# Cada entrada define una URL pública de la red social y la vista que debe
# procesarla. Los nombres de ruta se usan luego en templates y redirecciones.
urlpatterns = [
    path('', views.VistaInicioSocial.as_view(), name='social_home'),
    path('profile/', views.VistaPerfilUsuario.as_view(), name='profile'),
    path('profile/edit/', views.VistaEditarPerfil.as_view(), name='edit_profile'),
    path('profile/<str:username>/add_friend/', views.VistaAgregarAmigo.as_view(), name='add_friend'),
    path('profile/<str:username>/', views.VistaPerfilAjeno.as_view(), name='user_profile'),
    path('posts/new/', views.VistaCrearPublicacion.as_view(), name='create_post'),
    path('posts/<int:pk>/', views.VistaDetallePublicacion.as_view(), name='detalle_publicacion'),
    path('posts/<int:pk>/edit/', views.VistaEditarPublicacion.as_view(), name='editar_publicacion'),
    path('posts/<int:pk>/delete/', views.VistaEliminarPublicacion.as_view(), name='eliminar_publicacion'),
    path('login/', views.VistaIniciarSesion.as_view(), name='login'),
    path('logout/', views.VistaCerrarSesion.as_view(), name='logout'),
    path('register/', views.VistaRegistro.as_view(), name='register'),
]
