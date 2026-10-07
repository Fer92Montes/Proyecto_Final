from decimal import Decimal
from io import BytesIO
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

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

	def test_producto_con_talla_exige_talla_y_controla_stock_entre_tallas(self):
		"""Cada talla forma su línea de carrito y comparte el stock del producto."""
		self.producto.requires_size = True
		self.producto.stock = 3
		self.producto.save(update_fields=['requires_size', 'stock'])

		respuesta_sin_talla = self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '1'},
		)
		self.assertRedirects(respuesta_sin_talla, reverse('shop_home'))
		self.assertEqual(self.client.session.get('carrito', {}), {})

		self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '2', 'size': 'S'},
		)
		self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '2', 'size': 'M'},
		)
		self.assertEqual(
			self.client.session['carrito'],
			{f'{self.producto.pk}:S': 2},
		)
		resumen = self.client.get(reverse('ver_carrito'))
		self.assertContains(resumen, 'Talla: S')
		self.assertEqual(resumen.context['cart_count'], 2)

		respuesta_update = self.client.post(
			reverse('cart_update', args=[self.producto.pk]),
			{'quantity': '1', 'size': 'S'},
		)
		self.assertEqual(respuesta_update.status_code, 302)
		self.client.post(
			reverse('cart_remove', args=[self.producto.pk]),
			{'size': 'S'},
		)
		self.assertEqual(self.client.session['carrito'], {})

	def test_selector_de_talla_solo_se_muestra_para_productos_que_la_requieren(self):
		"""Catálogo y ficha muestran las cinco tallas cuando el producto las requiere."""
		self.producto.requires_size = True
		self.producto.save(update_fields=['requires_size'])

		respuesta_catalogo = self.client.get(reverse('shop_home'))
		respuesta_detalle = self.client.get(reverse('detalle_producto', args=[self.producto.pk]))
		for respuesta in (respuesta_catalogo, respuesta_detalle):
			self.assertContains(respuesta, 'name="size"')
			for talla in ('S', 'M', 'L', 'XL', 'XXL'):
				self.assertContains(respuesta, f'value="{talla}"')

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

	def test_administrador_crea_edita_y_elimina_producto_con_imagen(self):
		"""El panel permite mantener catálogo, stock, precio, descripción e imagen."""
		administrador = User.objects.create_superuser(
			username='admin_tienda',
			email='admin@example.com',
			password='ClaveSegura123!',
		)
		self.client.force_login(administrador)
		buffer = BytesIO()
		Image.new('RGB', (1, 1), color='green').save(buffer, format='PNG')
		contenido_imagen = buffer.getvalue()
		datos_imagen = SimpleUploadedFile(
			'producto.png',
			contenido_imagen,
			content_type='image/png',
		)

		with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
			respuesta_crear = self.client.post(
				reverse('admin:shop_abrazapinos_producto_add'),
				{
					'name': 'Casco de montaña',
					'description': 'Casco resistente para rutas.',
					'price': '34.90',
					'stock': '8',
					'image': datos_imagen,
					'_save': 'Guardar',
				},
			)
			self.assertEqual(respuesta_crear.status_code, 302)
			producto = Producto.objects.get(name='Casco de montaña')
			self.assertTrue(producto.image.name.startswith('productos/'))

			respuesta_editar = self.client.post(
				reverse('admin:shop_abrazapinos_producto_change', args=[producto.pk]),
				{
					'name': 'Casco de montaña',
					'description': 'Casco ligero actualizado.',
					'price': '39.90',
					'stock': '12',
					'_save': 'Guardar',
				},
			)
			self.assertEqual(respuesta_editar.status_code, 302)
			producto.refresh_from_db()
			self.assertEqual(producto.description, 'Casco ligero actualizado.')
			self.assertEqual(producto.price, Decimal('39.90'))
			self.assertEqual(producto.stock, 12)
			self.assertContains(
				self.client.get(reverse('shop_home')),
				f'src="{producto.image.url}"',
			)
			self.assertContains(
				self.client.get(reverse('detalle_producto', args=[producto.pk])),
				f'src="{producto.image.url}"',
			)

			respuesta_eliminar = self.client.post(
				reverse('admin:shop_abrazapinos_producto_delete', args=[producto.pk]),
				{'post': 'yes'},
			)
			self.assertEqual(respuesta_eliminar.status_code, 302)
			self.assertFalse(Producto.objects.filter(pk=producto.pk).exists())

	def test_gestion_de_productos_desde_la_tienda_requiere_permisos(self):
		"""Enlace y pantalla de gestión solo se ofrecen a cuentas autorizadas."""
		self.assertNotContains(self.client.get(reverse('shop_home')), 'Gestionar el catálogo')
		respuesta_sin_sesion = self.client.get(reverse('gestion_productos'))
		self.assertEqual(respuesta_sin_sesion.status_code, 302)

		usuario = User.objects.create_user(username='sin_permisos', password='ClaveSegura123!')
		self.client.force_login(usuario)
		self.assertEqual(self.client.get(reverse('gestion_productos')).status_code, 403)

		administrador = User.objects.create_superuser(
			username='admin_catalogo',
			email='admin@example.com',
			password='ClaveSegura123!',
		)
		self.client.force_login(administrador)
		respuesta_autorizada = self.client.get(reverse('gestion_productos'))
		self.assertEqual(respuesta_autorizada.status_code, 200)
		self.assertContains(self.client.get(reverse('shop_home')), 'Gestionar el catálogo')
		self.assertContains(respuesta_autorizada, 'Añadir producto')

		respuesta_crear = self.client.post(reverse('crear_producto'), {
			'name': 'Guantes de ciclismo',
			'description': 'Guantes para rutas largas.',
			'price': '19.95',
			'stock': '7',
		})
		self.assertEqual(respuesta_crear.status_code, 302)
		producto = Producto.objects.get(name='Guantes de ciclismo')

		respuesta_editar = self.client.post(
			reverse('editar_producto', args=[producto.pk]),
			{
				'name': 'Guantes de ciclismo',
				'description': 'Descripción actualizada.',
				'price': '21.95',
				'stock': '9',
			},
		)
		self.assertEqual(respuesta_editar.status_code, 302)
		producto.refresh_from_db()
		self.assertEqual(producto.description, 'Descripción actualizada.')
		self.assertEqual(producto.price, Decimal('21.95'))
		self.assertEqual(producto.stock, 9)

		respuesta_eliminar = self.client.post(
			reverse('eliminar_producto', args=[producto.pk]),
		)
		self.assertEqual(respuesta_eliminar.status_code, 302)
		self.assertFalse(Producto.objects.filter(pk=producto.pk).exists())

	def test_catalogo_pagina_seis_productos_y_conserva_busqueda(self):
		"""Verifica tamaño de página y que el enlace anterior conserva el filtro activo."""
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

	@override_settings(STRIPE_SECRET_KEY='sk_test_abrazapinos')
	@patch('shop_abrazapinos.views._cliente_stripe')
	def test_checkout_conserva_talla_en_pedido_y_checkout_stripe(self, crear_cliente):
		"""La talla elegida queda en la línea histórica y en el artículo de Stripe."""
		cliente = crear_cliente.return_value
		cliente.v1.checkout.sessions.create.return_value = SimpleNamespace(
			id='cs_test_talla',
			url='https://checkout.stripe.test/session',
		)
		self.producto.requires_size = True
		self.producto.save(update_fields=['requires_size'])
		self.client.post(
			reverse('cart_add', args=[self.producto.pk]),
			{'quantity': '1', 'size': 'XL'},
		)
		usuario = User.objects.create_user(username='cliente_talla', password='ClaveSegura123!')
		self.client.force_login(usuario)

		self.client.post(
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

		linea = LineaPedido.objects.get(pedido__usuario=usuario)
		self.assertEqual(linea.talla, 'XL')
		parametros = cliente.v1.checkout.sessions.create.call_args.kwargs['params']
		self.assertEqual(
			parametros['line_items'][0]['price_data']['product_data']['name'],
			'Bastones de marcha (Talla XL)',
		)

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
