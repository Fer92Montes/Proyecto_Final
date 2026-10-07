"""Configuración del panel de administración de la parte social."""

from django.contrib import admin

from .models import Post, Profile


@admin.action(description='Bloquear/ocultar publicaciones seleccionadas')
def ocultar_publicaciones(modeladmin, request, queryset):
    queryset.update(is_hidden=True)


@admin.action(description='Volver a mostrar publicaciones seleccionadas')
def mostrar_publicaciones(modeladmin, request, queryset):
    queryset.update(is_hidden=False)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Configura la gestión de publicaciones en el panel administrativo."""

    list_display = ('title', 'author', 'visibility', 'is_hidden', 'created_at')
    list_filter = ('is_hidden', 'visibility', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    actions = (ocultar_publicaciones, mostrar_publicaciones)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Configura la gestión de perfiles de usuarios en el panel administrativo."""

    list_display = ('user', 'city', 'created_at')
    search_fields = ('user__username', 'city', 'bio')
