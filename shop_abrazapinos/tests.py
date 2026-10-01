from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import LineaPedido, Pedido, Producto


class PruebasCarrito(TestCase):
	"""Comprueba carrito, acceso al checkout y confirmación de pedido con el cliente Django."""

	def setUp(self):
		"""Crea un producto aislado con precio y stock conocidos para cada caso."""
		self.producto = Producto.objects.create(
			name='Bastones de marcha',
			description='Bastones para rutas de montaña.',
			price=Decimal('24.50'),
			stock=5,
		)

	def test_anadir_producto_muestra_subtotal_y_total(self):
		"""Verifica la escritura de sesión y los importes derivados del precio unitario."""
		respuesta = self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '2', 'next': reverse('shop_home')},
		)

		self.assertRedirects(respuesta, reverse('shop_home'))
		respuesta = self.client.get(reverse('ver_carrito'))
		self.assertContains(respuesta, 'Bastones de marcha')
		self.assertContains(respuesta, '49.00')
		self.assertEqual(respuesta.context['cart_count'], 2)
		self.assertEqual(respuesta.context['cart_total'], Decimal('49.00'))

	def test_no_permite_superar_el_stock(self):
		"""Comprueba que una cantidad superior a existencias no altera la sesión."""
		respuesta = self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '6'},
		)

		self.assertRedirects(respuesta, reverse('shop_home'))
		self.assertEqual(self.client.session.get('carrito', {}), {})

	def test_catalogo_y_detalle_muestran_controles_de_compra(self):
		"""Asegura que catálogo y ficha muestran las acciones ligadas al carrito."""
		respuesta_catalogo = self.client.get(reverse('shop_home'))
		self.assertContains(respuesta_catalogo, 'Añadir al carrito')
		self.assertContains(respuesta_catalogo, 'Aumentar cantidad')
		self.assertContains(respuesta_catalogo, 'Ir al carrito')

		respuesta_detalle = self.client.get(
			reverse('detalle_producto', args=[self.producto.pk]),
		)
		self.assertContains(respuesta_detalle, 'Añadir al carrito')
		self.assertContains(respuesta_detalle, 'Reducir cantidad')

	def test_catalogo_busca_por_nombre_y_descripcion(self):
		"""Busca texto en ambos campos y devuelve el filtro para conservarlo en la vista."""
		otro_producto = Producto.objects.create(
			name='Cantimplora',
			description='Acero ligero para excursiones.',
			price=Decimal('12.00'),
			stock=3,
		)

		respuesta_nombre = self.client.get(reverse('shop_home'), {'q': 'Cantimplora'})
		self.assertContains(respuesta_nombre, otro_producto.name)
		self.assertNotContains(respuesta_nombre, self.producto.name)
		self.assertEqual(respuesta_nombre.context['search_query'], 'Cantimplora')

		respuesta_descripcion = self.client.get(reverse('shop_home'), {'q': 'excursiones'})
		self.assertContains(respuesta_descripcion, otro_producto.name)

	def test_catalogo_pagina_seis_productos_y_conserva_busqueda(self):
		for numero in range(8):
			Producto.objects.create(
				name=f'Producto especial {numero}',
				description='Artículo de prueba para el catálogo paginado.',
				price=Decimal('10.00'),
				stock=2,
			)

		respuesta = self.client.get(reverse('shop_home'), {'q': 'especial', 'page': '2'})
		self.assertEqual(respuesta.context['page_obj'].number, 2)
		self.assertEqual(len(respuesta.context['products']), 2)
		self.assertContains(respuesta, 'name="q" value="especial"')
		self.assertContains(respuesta, '?q=especial&amp;page=1')

	def test_eliminar_producto_vacia_el_carrito(self):
		"""Comprueba que la operación de eliminación quita el producto de la sesión."""
		self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '1'},
		)

		respuesta = self.client.post(
			reverse('cart_remove', args=[self.producto.pk]),
			{'next': reverse('ver_carrito')},
		)

		self.assertRedirects(respuesta, reverse('ver_carrito'))
		self.assertEqual(self.client.session.get('carrito', {}), {})
		self.assertContains(self.client.get(reverse('ver_carrito')), 'Tu carrito está vacío')

	def test_actualizar_cantidad_y_cero_elimina_la_linea(self):
		"""Valida el cambio de unidades y el convenio de cantidad cero como borrado."""
		self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '4'},
		)
		self.assertContains(self.client.get(reverse('shop_home')), 'Actualizar')
		self.assertContains(self.client.get(reverse('ver_carrito')), 'Actualizar')
		self.client.post(
			reverse('cart_update', args=[self.producto.pk]),
			{'quantity': '2', 'next': reverse('ver_carrito')},
		)
		self.assertEqual(self.client.session['carrito'][str(self.producto.pk)], 2)

		self.client.post(
			reverse('cart_update', args=[self.producto.pk]),
			{'quantity': '0', 'next': reverse('ver_carrito')},
		)
		self.assertEqual(self.client.session['carrito'], {})

	def test_checkout_de_invitado_ofrece_login_y_registro(self):
		"""Verifica que un invitado conserva acceso a login y alta desde el checkout."""
		self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '1'},
		)
		respuesta = self.client.get(reverse('tramitar_pedido'))

		self.assertContains(respuesta, 'Inicia sesión o crea una cuenta para continuar')
		self.assertContains(respuesta, "login/?next=/shop/tramitar-pedido/")
		self.assertContains(respuesta, "register/?next=/shop/tramitar-pedido/")

	@override_settings(STRIPE_SECRET_KEY='')
	def test_checkout_no_reserva_stock_si_stripe_no_esta_configurado(self):
		"""Evita crear pedidos o descontar stock si falta la clave de Stripe."""
		self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '1'},
		)
		usuario = User.objects.create_user(username='sin_stripe', password='ClaveSegura123!')
		self.client.force_login(usuario)

		respuesta = self.client.post(
			reverse('confirmar_pedido'),
			{
				'destinatario': 'Ana Ejemplo',
				'direccion': 'Calle de la Sierra 12',
				'ciudad': 'Baza',
				'provincia': 'Granada',
				'codigo_postal': '18800',
				'pais': 'España',
				'metodo_pago': 'stripe',
			},
		)

		self.assertRedirects(respuesta, reverse('tramitar_pedido'))
		self.assertFalse(Pedido.objects.exists())
		self.producto.refresh_from_db()
		self.assertEqual(self.producto.stock, 5)

	def test_login_y_registro_preservan_el_destino_de_checkout(self):
		"""Comprueba que ambos flujos de autenticación regresan al checkout indicado."""
		usuario = User.objects.create_user(username='comprador', password='ClaveSegura123!')
		respuesta_login = self.client.post(
			reverse('login'),
			{
				'username': usuario.username,
				'password': 'ClaveSegura123!',
				'next': reverse('tramitar_pedido'),
			},
		)
		self.assertRedirects(
			respuesta_login,
			reverse('tramitar_pedido'),
			fetch_redirect_response=False,
		)

		self.client.logout()
		respuesta_registro = self.client.post(
			reverse('register'),
			{
				'username': 'nuevo_comprador',
				'password1': 'ClaveSegura123!Otra',
				'password2': 'ClaveSegura123!Otra',
				'next': reverse('tramitar_pedido'),
			},
		)
		self.assertRedirects(
			respuesta_registro,
			reverse('tramitar_pedido'),
			fetch_redirect_response=False,
		)

	@override_settings(STRIPE_SECRET_KEY='sk_test_abrazapinos')
	@patch('shop_abrazapinos.views._cliente_stripe')
	def test_checkout_stripe_confirma_pedido_solo_tras_verificar_pago(self, crear_cliente):
		"""El pedido queda pendiente al crear checkout y se marca pagado al verificar Stripe."""
		cliente = crear_cliente.return_value
		cliente.v1.checkout.sessions.create.return_value = SimpleNamespace(
			id='cs_test_pedido',
			url='https://checkout.stripe.test/session',
		)
		self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '2'},
		)
		usuario = User.objects.create_user(username='cliente', password='ClaveSegura123!')
		self.client.force_login(usuario)
		respuesta_checkout = self.client.get(reverse('tramitar_pedido'))
		self.assertContains(respuesta_checkout, 'Nombre del destinatario')
		self.assertContains(respuesta_checkout, 'Dirección de entrega')
		self.assertContains(respuesta_checkout, 'Tarjeta bancaria mediante Stripe Checkout')
		self.assertContains(respuesta_checkout, 'name="metodo_pago" value="stripe"')

		respuesta = self.client.post(
			reverse('confirmar_pedido'),
			{
				'destinatario': 'Ana Ejemplo',
				'direccion': 'Calle de la Sierra 12',
				'ciudad': 'Baza',
				'provincia': 'Granada',
				'codigo_postal': '18800',
				'pais': 'España',
				'telefono': '600123123',
				'metodo_pago': 'stripe',
			},
		)

		pedido = Pedido.objects.get(usuario=usuario)
		linea = LineaPedido.objects.get(pedido=pedido)
		self.assertRedirects(respuesta, 'https://checkout.stripe.test/session', fetch_redirect_response=False)
		self.assertEqual(pedido.destinatario, 'Ana Ejemplo')
		self.assertEqual(pedido.metodo_pago, 'stripe')
		self.assertEqual(pedido.total, Decimal('49.00'))
		self.assertEqual(pedido.estado, 'pendiente_pago')
		self.assertEqual(pedido.stripe_session_id, 'cs_test_pedido')
		self.assertEqual(linea.cantidad, 2)
		self.assertEqual(linea.precio_unitario, Decimal('24.50'))
		self.producto.refresh_from_db()
		self.assertEqual(self.producto.stock, 3)
		self.assertEqual(self.client.session['carrito'][str(self.producto.pk)], 2)

		cliente.v1.checkout.sessions.retrieve.return_value = SimpleNamespace(payment_status='paid')
		respuesta_pago = self.client.get(
			reverse('stripe_success', args=[pedido.pk]),
			{'session_id': 'cs_test_pedido'},
		)
		self.assertRedirects(respuesta_pago, reverse('pedido_confirmado', args=[pedido.pk]))
		pedido.refresh_from_db()
		self.assertEqual(pedido.estado, 'pagado')
		self.assertEqual(self.client.session['carrito'], {})

	@override_settings(STRIPE_WEBHOOK_SECRET='whsec_test_abrazapinos')
	@patch('shop_abrazapinos.views.stripe.Webhook.construct_event')
	def test_webhook_stripe_marca_pago_idempotentemente(self, construir_evento):
		"""Acepta solo el evento validado y no repite efectos al recibirlo dos veces."""
		pedido = self._crear_pedido_pendiente()
		construir_evento.return_value = SimpleNamespace(
			type='checkout.session.completed',
			data=SimpleNamespace(object={
				'id': 'cs_test_pendiente',
				'payment_status': 'paid',
				'metadata': {'pedido_id': str(pedido.pk)},
			}),
		)

		for _ in range(2):
			respuesta = self.client.post(
				reverse('stripe_webhook'),
				data=b'{"type":"checkout.session.completed"}',
				content_type='application/json',
				HTTP_STRIPE_SIGNATURE='firma-simulada',
			)
			self.assertEqual(respuesta.status_code, 200)

		pedido.refresh_from_db()
		self.producto.refresh_from_db()
		self.assertEqual(pedido.estado, 'pagado')
		self.assertEqual(self.producto.stock, 4)

	@override_settings(STRIPE_WEBHOOK_SECRET='whsec_test_abrazapinos')
	@patch('shop_abrazapinos.views.stripe.Webhook.construct_event')
	def test_webhook_de_expiracion_libera_stock_una_sola_vez(self, construir_evento):
		"""Devuelve las unidades reservadas al inventario cuando vence una sesión."""
		pedido = self._crear_pedido_pendiente()
		construir_evento.return_value = SimpleNamespace(
			type='checkout.session.expired',
			data=SimpleNamespace(object={
				'id': 'cs_test_pendiente',
				'metadata': {'pedido_id': str(pedido.pk)},
			}),
		)

		for _ in range(2):
			respuesta = self.client.post(
				reverse('stripe_webhook'),
				data=b'{"type":"checkout.session.expired"}',
				content_type='application/json',
				HTTP_STRIPE_SIGNATURE='firma-simulada',
			)
			self.assertEqual(respuesta.status_code, 200)

		pedido.refresh_from_db()
		self.producto.refresh_from_db()
		self.assertEqual(pedido.estado, 'cancelado')
		self.assertEqual(self.producto.stock, 5)

	@override_settings(STRIPE_WEBHOOK_SECRET='whsec_test_abrazapinos')
	@patch('shop_abrazapinos.views.stripe.Webhook.construct_event', side_effect=ValueError)
	def test_webhook_rechaza_firma_invalida(self, construir_evento):
		"""No procesa cuerpos cuya firma Stripe no puede validarse."""
		respuesta = self.client.post(
			reverse('stripe_webhook'),
			data=b'{}',
			content_type='application/json',
			HTTP_STRIPE_SIGNATURE='firma-invalida',
		)
		self.assertEqual(respuesta.status_code, 400)

	def _crear_pedido_pendiente(self):
		"""Crea una orden de prueba con una unidad ya reservada en inventario."""
		self.producto.stock = 4
		self.producto.save(update_fields=['stock'])
		usuario = User.objects.create_user(username='cliente_stripe', password='ClaveSegura123!')
		pedido = Pedido.objects.create(
			usuario=usuario,
			destinatario='Ana Ejemplo',
			direccion='Calle de la Sierra 12',
			ciudad='Baza',
			provincia='Granada',
			codigo_postal='18800',
			pais='España',
			metodo_pago='stripe',
			total=Decimal('24.50'),
			estado='pendiente_pago',
			stripe_session_id='cs_test_pendiente',
		)
		LineaPedido.objects.create(
			pedido=pedido,
			producto=self.producto,
			nombre_producto=self.producto.name,
			precio_unitario=self.producto.price,
			cantidad=1,
		)
		return pedido
