"""Configuración del panel de administración de la parte social."""

from django.contrib import admin

from .models import Post, Profile


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Configura la gestión de publicaciones en el panel administrativo."""

    list_display = ('title', 'created_at')
    search_fields = ('title', 'content')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Configura la gestión de perfiles de usuarios en el panel administrativo."""

    list_display = ('user', 'city', 'created_at')
    search_fields = ('user__username', 'city', 'bio')
