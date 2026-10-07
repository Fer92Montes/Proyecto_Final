"""Pruebas del comportamiento social principal de la aplicación."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from shop_abrazapinos.models import LineaPedido, Pedido, Producto

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

    def test_feed_incluye_salto_accesible_al_contenido(self):
        """Comprueba que teclado y lector de pantalla alcanzan el contenido principal."""
        response = self.client.get(reverse('social_home'))
        self.assertContains(response, 'Saltar al contenido')
        self.assertContains(response, 'id="main-content" tabindex="-1"')

    def test_busqueda_feed_filtra_solo_publicaciones_visibles(self):
        """Busca texto del feed sin saltarse las reglas de visibilidad del servicio."""
        Post.objects.create(
            author=self.user,
            title='Palabra pública',
            content='Descripción indexable',
            visibility='public',
        )
        Post.objects.create(
            author=self.other,
            title='Palabra confidencial',
            content='No debe aparecer a visitantes',
            visibility='private',
        )

        response = self.client.get(reverse('social_home'), {'q': 'Palabra'})

        self.assertContains(response, 'Palabra pública')
        self.assertNotContains(response, 'Palabra confidencial')
        self.assertEqual(response.context['result_count'], 1)
        self.assertEqual(response.context['search_query'], 'Palabra')

    def test_publicacion_oculta_no_es_visible_ni_para_su_autor(self):
        """La moderación oculta publicaciones del feed, perfil y detalle."""
        publicacion = Post.objects.create(
            author=self.user,
            title='Publicación bloqueada',
            content='Contenido moderado',
            visibility='public',
            is_hidden=True,
        )

        self.client.force_login(self.user)
        response_feed = self.client.get(reverse('social_home'))
        response_detalle = self.client.get(reverse('detalle_publicacion', args=[publicacion.pk]))

        self.assertNotContains(response_feed, publicacion.title)
        self.assertEqual(response_feed.context['result_count'], 0)
        self.assertEqual(response_detalle.status_code, 404)

    def test_administrador_puede_ocultar_y_restaurar_publicaciones(self):
        """Las acciones del panel bloquean y vuelven a mostrar publicaciones."""
        administrador = User.objects.create_superuser(
            username='admin_social',
            email='admin@example.com',
            password='ClaveSegura123!',
        )
        publicacion = Post.objects.create(
            author=self.user,
            title='Publicación moderable',
            content='Contenido público',
            visibility='public',
        )
        self.client.force_login(administrador)
        url_admin = reverse('admin:social_abrazapinos_post_changelist')

        respuesta_ocultar = self.client.post(url_admin, {
            'action': 'ocultar_publicaciones',
            '_selected_action': [publicacion.pk],
            'index': 0,
        })
        publicacion.refresh_from_db()
        self.assertEqual(respuesta_ocultar.status_code, 302)
        self.assertTrue(publicacion.is_hidden)

        respuesta_mostrar = self.client.post(url_admin, {
            'action': 'mostrar_publicaciones',
            '_selected_action': [publicacion.pk],
            'index': 0,
        })
        publicacion.refresh_from_db()
        self.assertEqual(respuesta_mostrar.status_code, 302)
        self.assertFalse(publicacion.is_hidden)

    def test_pantalla_de_moderacion_solo_aparece_y_abre_con_permiso(self):
        """La gestión social está enlazada en el feed y bloqueada sin permisos."""
        respuesta_anonima = self.client.get(reverse('gestion_publicaciones'))
        self.assertEqual(respuesta_anonima.status_code, 302)

        self.client.force_login(self.user)
        respuesta_sin_permiso = self.client.get(reverse('gestion_publicaciones'))
        self.assertEqual(respuesta_sin_permiso.status_code, 403)
        self.assertNotContains(self.client.get(reverse('social_home')), 'Moderar publicaciones')

        administrador = User.objects.create_superuser(
            username='admin_moderacion',
            email='admin@example.com',
            password='ClaveSegura123!',
        )
        self.client.force_login(administrador)
        respuesta_autorizada = self.client.get(reverse('gestion_publicaciones'))
        self.assertEqual(respuesta_autorizada.status_code, 200)
        self.assertContains(self.client.get(reverse('social_home')), 'Moderar publicaciones')

    def test_feed_social_pagina_seis_publicaciones_y_conserva_busqueda(self):
        """Comprueba seis publicaciones por página y retención de q entre páginas."""
        for numero in range(8):
            Post.objects.create(
                author=self.user,
                title=f'Ruta comunitaria {numero}',
                content='Publicación de senderismo para comprobar el paginador.',
                visibility='public',
            )

        response = self.client.get(reverse('social_home'), {'q': 'senderismo', 'page': '2'})

        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['posts']), 2)
        self.assertEqual(response.context['result_count'], 8)
        self.assertEqual(response.context['search_query'], 'senderismo')
        self.assertContains(response, 'aria-label="Paginación de publicaciones"')
        self.assertContains(response, '?q=senderismo&amp;page=1')

    def test_authenticated_user_can_access_profile(self):
        """Comprueba que un usuario autenticado puede ver su perfil privado."""
        self.client.login(username='ana', password='Test1234')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_perfil_muestra_solo_historial_de_compras_confirmadas_del_usuario(self):
        """El perfil incluye artículos comprados con talla y excluye otros pedidos."""
        producto = Producto.objects.create(
            name='Camiseta del club',
            description='Camiseta técnica.',
            price='25.00',
            stock=4,
            requires_size=True,
        )
        pedido_pagado = Pedido.objects.create(
            usuario=self.user,
            destinatario='Ana',
            direccion='Calle 1',
            ciudad='Baza',
            provincia='Granada',
            codigo_postal='18800',
            pais='España',
            metodo_pago='stripe',
            total='50.00',
            estado='pagado',
        )
        LineaPedido.objects.create(
            pedido=pedido_pagado,
            producto=producto,
            nombre_producto='Camiseta del club',
            precio_unitario='25.00',
            cantidad=2,
            talla='M',
        )
        pedido_pendiente = Pedido.objects.create(
            usuario=self.user,
            destinatario='Ana',
            direccion='Calle 1',
            ciudad='Baza',
            provincia='Granada',
            codigo_postal='18800',
            pais='España',
            metodo_pago='stripe',
            total='25.00',
            estado='pendiente_pago',
        )
        LineaPedido.objects.create(
            pedido=pedido_pendiente,
            producto=producto,
            nombre_producto='Pedido sin pagar',
            precio_unitario='25.00',
            cantidad=1,
        )
        pedido_ajeno = Pedido.objects.create(
            usuario=self.friend,
            destinatario='Luis',
            direccion='Calle 2',
            ciudad='Baza',
            provincia='Granada',
            codigo_postal='18800',
            pais='España',
            metodo_pago='stripe',
            total='25.00',
            estado='pagado',
        )
        LineaPedido.objects.create(
            pedido=pedido_ajeno,
            producto=producto,
            nombre_producto='Compra de otra persona',
            precio_unitario='25.00',
            cantidad=1,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))

        self.assertContains(response, 'Historial de compras')
        self.assertContains(response, 'Camiseta del club')
        self.assertContains(response, 'Talla M')
        self.assertContains(response, 'Pedido #{}'.format(pedido_pagado.pk))
        self.assertNotContains(response, 'Pedido #{}'.format(pedido_pendiente.pk))
        self.assertNotContains(response, 'Compra de otra persona')

    def test_login_y_registro_sin_destino_vuelven_al_feed_social(self):
        """Comprueba que el feed es el destino predeterminado tras autenticarse."""
        respuesta_login = self.client.post(
            reverse('login'),
            {'username': 'ana', 'password': 'Test1234'},
        )
        self.assertRedirects(respuesta_login, reverse('social_home'), fetch_redirect_response=False)

        self.client.logout()
        respuesta_registro = self.client.post(
            reverse('register'),
            {
                'username': 'nueva_usuaria',
                'password1': 'ClaveSegura123!Otra',
                'password2': 'ClaveSegura123!Otra',
            },
        )
        self.assertRedirects(respuesta_registro, reverse('social_home'), fetch_redirect_response=False)

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
