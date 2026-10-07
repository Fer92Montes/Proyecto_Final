"""Configuración del panel de administración de la parte social."""

from django.contrib import admin

from .models import Post, Profile


@admin.action(description='Bloquear/ocultar publicaciones seleccionadas')
def ocultar_publicaciones(modeladmin, request, queryset):
    """Suspende en bloque posts seleccionados sin borrar su contenido ni imagen."""
    queryset.update(is_hidden=True)


@admin.action(description='Volver a mostrar publicaciones seleccionadas')
def mostrar_publicaciones(modeladmin, request, queryset):
    """Restaura en bloque la visibilidad normal de posts moderados."""
    queryset.update(is_hidden=False)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Expone moderación, búsqueda y filtros de estado en Django Admin."""

    list_display = ('title', 'author', 'visibility', 'is_hidden', 'created_at')
    list_filter = ('is_hidden', 'visibility', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    actions = (ocultar_publicaciones, mostrar_publicaciones)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Configura la gestión de perfiles de usuarios en el panel administrativo."""

    list_display = ('user', 'city', 'created_at')
    search_fields = ('user__username', 'city', 'bio')
