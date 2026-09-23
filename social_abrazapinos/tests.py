"""Pruebas del comportamiento social principal de la aplicación."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from shop_abrazapinos.models import Producto

from .models import Friendship, Post, Profile


class PruebasAppSocial(TestCase):
    """Comprueba la seguridad del perfil y la visibilidad de contenido entre usuarios."""

    def setUp(self):
        """Prepara usuarios y perfiles usados en las pruebas del feed social."""
        self.user = User.objects.create_user(username='ana', password='Test1234')
        self.friend = User.objects.create_user(username='luis', password='Test1234')
        self.other = User.objects.create_user(username='marta', password='Test1234')
        Profile.objects.get_or_create(user=self.user)
        Profile.objects.get_or_create(user=self.friend)
        Profile.objects.get_or_create(user=self.other)

    def test_profile_requires_login(self):
        """Verifica que un usuario no autenticado no pueda entrar al perfil privado."""
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/social/login/', response.headers.get('Location', ''))

    def test_authenticated_user_can_access_profile(self):
        """Comprueba que un usuario autenticado puede ver su perfil privado."""
        self.client.login(username='ana', password='Test1234')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_friend_relationship_and_friend_visibility(self):
        """Valida que la relación de amistad y la visibilidad de posts funciona."""
        self.client.login(username='ana', password='Test1234')
        response = self.client.get(reverse('add_friend', args=['luis']))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Friendship.objects.filter(from_user=self.user, to_user=self.friend).exists())

        Post.objects.create(
            author=self.friend,
            title='Post de amigo',
            content='Contenido visible para amigos',
            visibility='friends',
        )

        response = self.client.get(reverse('social_home'))
        self.assertContains(response, 'Post de amigo')

    def test_post_detail_is_accessible(self):
        """Comprueba que una publicación pública tiene una vista detallada accesible."""
        publicacion = Post.objects.create(
            author=self.user,
            title='Detalle de prueba',
            content='Contenido completo de la publicación',
            visibility='public',
        )

        response = self.client.get(reverse('detalle_publicacion', args=[publicacion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detalle de prueba')
        self.assertContains(response, 'Contenido completo de la publicación')

    def test_product_detail_is_accessible(self):
        """Comprueba que un producto tiene una vista detallada correcta."""
        producto = Producto.objects.create(
            name='Bicicleta de prueba',
            description='Una bicicleta para ver su detalle',
            price='499.99',
            stock=5,
        )

        response = self.client.get(reverse('detalle_producto', args=[producto.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bicicleta de prueba')
        self.assertContains(response, '499.99')

    def test_profile_posts_include_detail_link(self):
        """Verifica que las publicaciones del perfil tienen acceso a su detalle."""
        publicacion = Post.objects.create(
            author=self.user,
            title='Publicación del perfil',
            content='Contenido con detalle disponible',
            visibility='public',
        )

        self.client.login(username='ana', password='Test1234')
        response = self.client.get(reverse('profile'))
        self.assertContains(response, reverse('detalle_publicacion', args=[publicacion.pk]))

    def test_author_can_edit_post_from_detail_view(self):
        """Comprueba que el autor puede editar su publicación desde la vista detallada."""
        publicacion = Post.objects.create(
            author=self.user,
            title='Título original',
            content='Contenido original',
            visibility='public',
        )

        self.client.login(username='ana', password='Test1234')
        response = self.client.get(reverse('editar_publicacion', args=[publicacion.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('editar_publicacion', args=[publicacion.pk]),
            {'title': 'Título actualizado', 'content': 'Contenido actualizado', 'visibility': 'friends'},
        )
        self.assertEqual(response.status_code, 302)
        publicacion.refresh_from_db()
        self.assertEqual(publicacion.title, 'Título actualizado')
        self.assertEqual(publicacion.content, 'Contenido actualizado')

    def test_author_can_delete_post_from_detail_view(self):
        """Comprueba que el autor puede borrar su publicación desde la vista detallada."""
        publicacion = Post.objects.create(
            author=self.user,
            title='Publicación para borrar',
            content='Contenido que se eliminará',
            visibility='public',
        )

        self.client.login(username='ana', password='Test1234')
        response = self.client.post(reverse('eliminar_publicacion', args=[publicacion.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(pk=publicacion.pk).exists())

    def test_other_user_profile_has_top_return_link(self):
        """Comprueba que el perfil ajeno muestra el acceso rápido a la social en la cabecera."""
        self.client.login(username='ana', password='Test1234')
        response = self.client.get(reverse('user_profile', args=['luis']))
        self.assertContains(response, 'Volver a la social')
        self.assertContains(response, reverse('social_home'))
