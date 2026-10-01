"""Vistas de la aplicación de tienda."""

import logging
from datetime import timedelta
from decimal import Decimal

import stripe
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from .forms import FormularioTramitarPedido
from .models import LineaPedido, Pedido, Producto

logger = logging.getLogger(__name__)


def _cliente_stripe():
    """Crea un cliente Stripe con la clave de entorno sin modificar estado global."""
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def obtener_resumen_carrito(request):
    """Normaliza las cantidades de sesión y prepara importes para las plantillas."""
    # La sesión almacena solo ID y cantidad; se descartan datos malformados antes
    # de consultar modelos para no confiar en valores controlados por el navegador.
    carrito_sesion = request.session.get('carrito', {})
    if not isinstance(carrito_sesion, dict):
        carrito_sesion = {}
    cantidades = {}

    for identificador, cantidad in carrito_sesion.items():
        try:
            producto_id = int(identificador)
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue
        if producto_id > 0 and cantidad > 0:
            cantidades[producto_id] = cantidad

    # in_bulk recupera todos los productos en una consulta y permite indexarlos por PK.
    productos = Producto.objects.in_bulk(cantidades)
    carrito_normalizado = {}
    lineas = []

    for producto_id, cantidad in cantidades.items():
        producto = productos.get(producto_id)
        if producto is None or producto.stock <= 0:
            continue
        # Si el stock bajó desde que se añadió el artículo, el resumen nunca promete más.
        cantidad = min(cantidad, producto.stock)
        carrito_normalizado[str(producto_id)] = cantidad
        lineas.append({
            'product': producto,
            'quantity': cantidad,
            'subtotal': producto.price * cantidad,
        })

    # Persistir la forma normalizada limpia productos borrados y cantidades inválidas.
    if carrito_normalizado != carrito_sesion:
        request.session['carrito'] = carrito_normalizado

    return {
        'cart_items': lineas,
        'cart_count': sum(linea['quantity'] for linea in lineas),
        'cart_total': sum((linea['subtotal'] for linea in lineas), Decimal('0.00')),
    }


def _redireccion_carrito(request, destino_por_defecto):
    """Solo acepta destinos de retorno pertenecientes al mismo sitio."""
    # La validación de host evita redirecciones externas controladas por POST `next`.
    destino = request.POST.get('next', '')
    if destino and url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destino)
    return redirect(destino_por_defecto)


class VistaTienda(TemplateView):
    """Filtra y pagina el catálogo antes de mostrarlo en la tienda."""

    template_name = 'shop_abrazapinos/home.html'

    def get_context_data(self, **kwargs):
        """Añade la página de productos, el filtro y el resumen del carrito."""
        contexto = super().get_context_data(**kwargs)
        consulta = self.request.GET.get('q', '').strip()
        productos = Producto.objects.order_by('-created_at')
        if consulta:
            productos = productos.filter(
                Q(name__icontains=consulta) | Q(description__icontains=consulta)
            )

        # El paginador evita renderizar todo el catálogo y mantiene la búsqueda al avanzar.
        pagina = Paginator(productos, 6).get_page(self.request.GET.get('page'))
        contexto['products'] = pagina
        contexto['page_obj'] = pagina
        contexto['search_query'] = consulta
        contexto['result_count'] = pagina.paginator.count
        # El resumen compartido alimenta el contador y el desplegable de la cabecera.
        contexto.update(obtener_resumen_carrito(self.request))
        return contexto


class VistaDetalleProducto(TemplateView):
    """Muestra el detalle completo de un producto de la tienda."""

    template_name = 'shop_abrazapinos/product_detail.html'

    def get_context_data(self, **kwargs):
        """Añade el producto actual y su información completa al contexto."""
        contexto = super().get_context_data(**kwargs)
        contexto['product'] = get_object_or_404(Producto, pk=self.kwargs.get('pk'))
        # La misma estructura de carrito está disponible en la ficha de producto.
        contexto.update(obtener_resumen_carrito(self.request))
        return contexto


def inicio(request):
    """Mantiene una vista funcional con el nombre más claro del proyecto."""
    return VistaTienda.as_view()(request)


def ver_carrito(request):
    """Muestra los productos, subtotales y total guardados en la sesión."""
    contexto = obtener_resumen_carrito(request)
    return render(request, 'shop_abrazapinos/cart.html', contexto)


@require_POST
def anadir_al_carrito(request, pk):
    """Añade una cantidad al carrito sin permitir superar las existencias."""
    producto = get_object_or_404(Producto, pk=pk)
    try:
        cantidad = int(request.POST.get('quantity', '1'))
    except (TypeError, ValueError):
        cantidad = 0

    # Se suma a la cantidad existente y se valida el total acumulado, no solo el envío actual.
    carrito = request.session.get('carrito', {})
    cantidad_actual = int(carrito.get(str(producto.pk), 0))
    if cantidad <= 0:
        messages.error(request, 'Indica una cantidad válida.')
    elif cantidad_actual + cantidad > producto.stock:
        messages.error(request, 'La cantidad solicitada supera el stock disponible.')
    else:
        carrito[str(producto.pk)] = cantidad_actual + cantidad
        request.session['carrito'] = carrito
        messages.success(request, f'{producto.name} se ha añadido al carrito.')

    return _redireccion_carrito(request, 'shop_home')


@require_POST
def quitar_del_carrito(request, pk):
    """Elimina por completo un producto del carrito de sesión."""
    carrito = request.session.get('carrito', {})
    carrito.pop(str(pk), None)
    request.session['carrito'] = carrito
    messages.info(request, 'Se ha eliminado el producto del carrito.')
    return _redireccion_carrito(request, 'ver_carrito')


@require_POST
def actualizar_cantidad_carrito(request, pk):
    """Establece la cantidad deseada; cero elimina la línea del carrito."""
    producto = get_object_or_404(Producto, pk=pk)
    try:
        cantidad = int(request.POST.get('quantity', ''))
    except (TypeError, ValueError):
        cantidad = -1

    carrito = request.session.get('carrito', {})
    if not isinstance(carrito, dict):
        carrito = {}

    # Cero es una operación válida de eliminación; valores negativos o mayores al stock no.
    if cantidad < 0:
        messages.error(request, 'Indica una cantidad válida.')
    elif cantidad == 0:
        carrito.pop(str(producto.pk), None)
        request.session['carrito'] = carrito
        messages.info(request, f'{producto.name} se ha quitado del carrito.')
    elif cantidad > producto.stock:
        messages.error(request, 'La cantidad solicitada supera el stock disponible.')
    else:
        carrito[str(producto.pk)] = cantidad
        request.session['carrito'] = carrito
        messages.success(request, f'Cantidad de {producto.name} actualizada.')

    return _redireccion_carrito(request, 'ver_carrito')


@require_GET
def tramitar_pedido(request):
    """Muestra el acceso para invitados o el formulario de envío para clientes."""
    # No se muestra un formulario de compra vacío; primero se requiere una línea válida.
    contexto = obtener_resumen_carrito(request)
    if not contexto['cart_items']:
        messages.info(request, 'Añade productos al carrito antes de tramitar un pedido.')
        return redirect('ver_carrito')

    contexto['form'] = FormularioTramitarPedido(initial={
        'destinatario': request.user.get_full_name() if request.user.is_authenticated else '',
    })
    contexto['checkout_requires_login'] = not request.user.is_authenticated
    return render(request, 'shop_abrazapinos/checkout.html', contexto)


@require_POST
def confirmar_pedido(request):
    """Reserva existencias y redirige a la página segura de Stripe Checkout."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('tramitar_pedido')}")

    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, 'Stripe no está configurado. Revisa las variables de entorno.')
        return redirect('tramitar_pedido')

    contexto = obtener_resumen_carrito(request)
    if not contexto['cart_items']:
        messages.info(request, 'Añade productos al carrito antes de tramitar un pedido.')
        return redirect('ver_carrito')

    formulario = FormularioTramitarPedido(request.POST)
    if not formulario.is_valid():
        contexto['form'] = formulario
        contexto['checkout_requires_login'] = False
        return render(request, 'shop_abrazapinos/checkout.html', contexto)

    # Se reconstruye la selección desde la sesión y la base, nunca desde precios del POST.
    cantidades = {item['product'].pk: item['quantity'] for item in contexto['cart_items']}
    pedido = None
    stock_valido = True

    # La reserva impide vender las mismas unidades mientras Stripe procesa el pago.
    with transaction.atomic():
        # select_for_update bloquea las filas en motores que soportan bloqueo pesimista,
        # evitando que dos confirmaciones consuman simultáneamente las mismas unidades.
        productos = {
            producto.pk: producto
            for producto in Producto.objects.select_for_update().filter(pk__in=cantidades)
        }
        if len(productos) != len(cantidades) or any(
            productos[producto_id].stock < cantidad
            for producto_id, cantidad in cantidades.items()
            if producto_id in productos
        ):
            stock_valido = False
        else:
            total = sum(
                (productos[producto_id].price * cantidad for producto_id, cantidad in cantidades.items()),
                Decimal('0.00'),
            )
            pedido = Pedido.objects.create(
                usuario=request.user,
                destinatario=formulario.cleaned_data['destinatario'],
                direccion=formulario.cleaned_data['direccion'],
                ciudad=formulario.cleaned_data['ciudad'],
                provincia=formulario.cleaned_data['provincia'],
                codigo_postal=formulario.cleaned_data['codigo_postal'],
                pais=formulario.cleaned_data['pais'],
                telefono=formulario.cleaned_data['telefono'],
                metodo_pago=formulario.cleaned_data['metodo_pago'],
                total=total,
                estado='pendiente_pago',
            )
            # El detalle conserva el nombre y el precio aplicados, aunque luego cambie el catálogo.
            for producto_id, cantidad in cantidades.items():
                producto = productos[producto_id]
                LineaPedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    nombre_producto=producto.name,
                    precio_unitario=producto.price,
                    cantidad=cantidad,
                )
                # La cantidad se descuenta como reserva y se repone si Stripe cancela o caduca.
                producto.stock -= cantidad
                producto.save(update_fields=['stock'])

    if not stock_valido:
        messages.error(request, 'El stock ha cambiado. Revisa las cantidades antes de continuar.')
        return redirect('ver_carrito')

    # Stripe recibe importes calculados desde las líneas persistidas en el servidor.
    line_items = [
        {
            'price_data': {
                'currency': settings.STRIPE_CURRENCY,
                'product_data': {'name': linea.nombre_producto},
                'unit_amount': int(linea.precio_unitario * 100),
            },
            'quantity': linea.cantidad,
        }
        for linea in pedido.lineas.all()
    ]
    dominio = request.build_absolute_uri('/').rstrip('/')
    try:
        # StripeClient mantiene la clave aislada por instancia y recibe solo datos calculados aquí.
        cliente = _cliente_stripe()
        sesion_pago = cliente.v1.checkout.sessions.create(params={
                'mode': 'payment',
                'line_items': line_items,
                'client_reference_id': str(pedido.pk),
                'metadata': {'pedido_id': str(pedido.pk)},
                'success_url': (
                    f"{dominio}{reverse('stripe_success', args=[pedido.pk])}"
                    '?session_id={CHECKOUT_SESSION_ID}'
                ),
                'cancel_url': f"{dominio}{reverse('stripe_cancel', args=[pedido.pk])}",
                # Se supera levemente el mínimo de Stripe para absorber la latencia de red.
                'expires_at': int((timezone.now() + timedelta(minutes=35)).timestamp()),
                'customer_email': request.user.email or None,
            })
    except stripe.StripeError:
        logger.exception('No se pudo crear la sesión de pago para el pedido %s.', pedido.pk)
        _cancelar_pedido_y_liberar_stock(pedido.pk)
        messages.error(request, 'No se pudo iniciar el pago con Stripe. Inténtalo de nuevo.')
        return redirect('tramitar_pedido')

    pedido.stripe_session_id = sesion_pago.id
    pedido.save(update_fields=['stripe_session_id'])
    # El carrito permanece intacto hasta que el pago quede confirmado por Stripe.
    return redirect(sesion_pago.url)


def _marcar_pedido_pagado(pedido_id, session_id):
    """Marca como pagado solo el pedido ligado a la sesión Stripe verificada."""
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido_id)
        if pedido.stripe_session_id != session_id:
            return False
        if pedido.estado == 'pendiente_pago':
            pedido.estado = 'pagado'
            pedido.save(update_fields=['estado'])
        return pedido.estado == 'pagado'


def _cancelar_pedido_y_liberar_stock(pedido_id):
    """Cancela un pago pendiente y devuelve sus unidades una sola vez al inventario."""
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido_id)
        if pedido.estado != 'pendiente_pago':
            return False
        for linea in pedido.lineas.select_related('producto'):
            producto = Producto.objects.select_for_update().get(pk=linea.producto_id)
            producto.stock += linea.cantidad
            producto.save(update_fields=['stock'])
        pedido.estado = 'cancelado'
        pedido.save(update_fields=['estado'])
        return True


@require_GET
def stripe_success(request, pk):
    """Consulta a Stripe antes de mostrar la confirmación del pedido al comprador."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('tramitar_pedido')}")
    pedido = get_object_or_404(Pedido, pk=pk, usuario=request.user)
    session_id = request.GET.get('session_id', '')
    if not session_id or session_id != pedido.stripe_session_id:
        messages.error(request, 'No se pudo verificar la sesión de pago.')
        return redirect('ver_carrito')

    try:
        sesion_pago = _cliente_stripe().v1.checkout.sessions.retrieve(session_id)
    except stripe.StripeError:
        logger.exception('No se pudo consultar la sesión Stripe del pedido %s.', pedido.pk)
        messages.error(request, 'No se pudo comprobar el pago. Vuelve a intentarlo en unos instantes.')
        return redirect('ver_carrito')

    if sesion_pago.payment_status == 'paid' and _marcar_pedido_pagado(pedido.pk, session_id):
        request.session['carrito'] = {}
        return redirect('pedido_confirmado', pk=pedido.pk)

    messages.info(request, 'Stripe todavía está confirmando el pago. El pedido no se marcará como pagado hasta verificarlo.')
    return redirect('pedido_confirmado', pk=pedido.pk)


@require_GET
def stripe_cancel(request, pk):
    """Expira el Checkout cancelado y libera la reserva si Stripe lo permite."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('tramitar_pedido')}")
    pedido = get_object_or_404(Pedido, pk=pk, usuario=request.user)
    if pedido.estado == 'pendiente_pago' and pedido.stripe_session_id and settings.STRIPE_SECRET_KEY:
        try:
            cliente = _cliente_stripe()
            cliente.v1.checkout.sessions.expire(pedido.stripe_session_id)
            _cancelar_pedido_y_liberar_stock(pedido.pk)
        except stripe.StripeError:
            # El webhook checkout.session.expired liberará la reserva si la API falla aquí.
            logger.exception('No se pudo cancelar la sesión Stripe del pedido %s.', pedido.pk)
    messages.info(request, 'Has cancelado el pago. No se ha realizado ningún cobro.')
    return redirect('ver_carrito')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Valida la firma Stripe y procesa pagos o expiraciones de forma idempotente."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=500)
    firma = request.headers.get('Stripe-Signature', '')
    try:
        evento = stripe.Webhook.construct_event(
            request.body,
            firma,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    sesion_pago = evento.data.object
    pedido_id = (sesion_pago.get('metadata') or {}).get('pedido_id')
    if not pedido_id:
        return HttpResponse(status=200)

    if evento.type in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
        if sesion_pago.get('payment_status') == 'paid':
            _marcar_pedido_pagado(pedido_id, sesion_pago.get('id'))
    elif evento.type in ('checkout.session.expired', 'checkout.session.async_payment_failed'):
        _cancelar_pedido_y_liberar_stock(pedido_id)
    return HttpResponse(status=200)


@require_GET
def pedido_confirmado(request, pk):
    """Muestra la confirmación únicamente al usuario propietario del pedido."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('tramitar_pedido')}")
    # Filtrar por propietario evita que otro usuario consulte un pedido por su ID.
    pedido = get_object_or_404(Pedido, pk=pk, usuario=request.user)
    if pedido.estado == 'pendiente_pago':
        messages.info(request, 'El pago sigue pendiente de confirmación de Stripe.')
    return render(request, 'shop_abrazapinos/order_confirmation.html', {'pedido': pedido})


home = inicio

__all__ = [
    'VistaTienda',
    'VistaDetalleProducto',
    'anadir_al_carrito',
    'actualizar_cantidad_carrito',
    'confirmar_pedido',
    'inicio',
    'home',
    'quitar_del_carrito',
    'pedido_confirmado',
    'stripe_cancel',
    'stripe_success',
    'stripe_webhook',
    'tramitar_pedido',
    'ver_carrito',
]
