"""Vistas de la aplicación de tienda."""

import logging
from datetime import timedelta
from decimal import Decimal

import stripe
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.storage import default_storage
from django.db.models import ProtectedError
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

from .forms import FormularioProducto, FormularioTramitarPedido
from .models import LineaPedido, Pedido, Producto

logger = logging.getLogger(__name__)

TALLAS_VALIDAS = {talla for talla, _ in Producto.TALLAS}
PERMISO_PRODUCTO_ADD = 'shop_abrazapinos.add_producto'
PERMISO_PRODUCTO_CHANGE = 'shop_abrazapinos.change_producto'
PERMISO_PRODUCTO_DELETE = 'shop_abrazapinos.delete_producto'


class VistaGestionProductos(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Muestra a personal autorizado el catálogo y las acciones disponibles."""

    template_name = 'shop_abrazapinos/management.html'
    login_url = 'login'

    def test_func(self):
        """Permite entrar si la cuenta tiene algún permiso de catálogo."""
        return any(self.request.user.has_perm(permiso) for permiso in (
            PERMISO_PRODUCTO_ADD,
            PERMISO_PRODUCTO_CHANGE,
            PERMISO_PRODUCTO_DELETE,
        ))

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update({
            'products': Producto.objects.all(),
            'can_add_product': self.request.user.has_perm(PERMISO_PRODUCTO_ADD),
            'can_change_product': self.request.user.has_perm(PERMISO_PRODUCTO_CHANGE),
            'can_delete_product': self.request.user.has_perm(PERMISO_PRODUCTO_DELETE),
        })
        return contexto


@login_required(login_url='login')
@permission_required(PERMISO_PRODUCTO_ADD, raise_exception=True)
def crear_producto(request):
    """Crea un artículo del catálogo con los datos e imagen enviados."""
    if request.method == 'POST':
        formulario = FormularioProducto(request.POST, request.FILES)
        if formulario.is_valid():
            producto = formulario.save()
            messages.success(request, f'El producto «{producto.name}» se ha creado.')
            return redirect('gestion_productos')
    else:
        formulario = FormularioProducto()
    return render(request, 'shop_abrazapinos/product_form.html', {
        'form': formulario,
        'page_title': 'Añadir producto',
    })


@login_required(login_url='login')
@permission_required(PERMISO_PRODUCTO_CHANGE, raise_exception=True)
def editar_producto(request, pk):
    """Actualiza un producto y limpia su imagen anterior al reemplazarla."""
    producto = get_object_or_404(Producto, pk=pk)
    imagen_anterior = producto.image.name
    if request.method == 'POST':
        formulario = FormularioProducto(request.POST, request.FILES, instance=producto)
        if formulario.is_valid():
            producto = formulario.save()
            if imagen_anterior and imagen_anterior != producto.image.name:
                default_storage.delete(imagen_anterior)
            messages.success(request, f'El producto «{producto.name}» se ha actualizado.')
            return redirect('gestion_productos')
    else:
        formulario = FormularioProducto(instance=producto)
    return render(request, 'shop_abrazapinos/product_form.html', {
        'form': formulario,
        'product': producto,
        'page_title': 'Editar producto',
    })


@login_required(login_url='login')
@permission_required(PERMISO_PRODUCTO_DELETE, raise_exception=True)
@require_POST
def eliminar_producto(request, pk):
    """Elimina un producto si no forma parte del historial protegido de pedidos."""
    producto = get_object_or_404(Producto, pk=pk)
    nombre = producto.name
    imagen = producto.image.name
    try:
        producto.delete()
    except ProtectedError:
        messages.error(
            request,
            f'No se puede eliminar «{nombre}» porque está incluido en pedidos existentes.',
        )
    else:
        if imagen:
            default_storage.delete(imagen)
        messages.success(request, f'El producto «{nombre}» se ha eliminado.')
    return redirect('gestion_productos')


def _cliente_stripe():
    """Crea un cliente Stripe con la clave de entorno sin modificar estado global."""
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def obtener_resumen_carrito(request):
    """Normaliza las cantidades de sesión y prepara importes para las plantillas."""
    # La sesión almacena ID/talla/cantidad; se descartan datos malformados.
    carrito_sesion = request.session.get('carrito', {})
    if not isinstance(carrito_sesion, dict):
        carrito_sesion = {}
    lineas_sesion = []
    ids_producto = set()

    for clave, cantidad in carrito_sesion.items():
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue
        producto_id, talla = _leer_clave_linea_carrito(clave)
        if producto_id is not None and cantidad > 0:
            lineas_sesion.append((producto_id, talla, cantidad))
            ids_producto.add(producto_id)

    # in_bulk recupera todos los productos en una consulta y permite indexarlos por PK.
    productos = Producto.objects.in_bulk(ids_producto)
    carrito_normalizado = {}
    lineas = []
    stock_restante = {producto_id: producto.stock for producto_id, producto in productos.items()}

    for producto_id, talla, cantidad in lineas_sesion:
        producto = productos.get(producto_id)
        if producto is None:
            continue
        if producto.requires_size and talla not in TALLAS_VALIDAS:
            continue
        if not producto.requires_size and talla:
            continue
        # Si el stock bajó desde que se añadió el artículo, el resumen nunca promete más.
        cantidad = min(cantidad, stock_restante[producto_id])
        if cantidad <= 0:
            continue
        stock_restante[producto_id] -= cantidad
        clave = _clave_linea_carrito(producto_id, talla)
        carrito_normalizado[clave] = cantidad
        lineas.append({
            'product': producto,
            'quantity': cantidad,
            'size': talla,
            'cart_key': clave,
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


def _clave_linea_carrito(producto_id, talla=''):
    """Construye una clave distinta para cada talla sin cambiar claves antiguas."""
    return f'{producto_id}:{talla}' if talla else str(producto_id)


def _leer_clave_linea_carrito(clave):
    """Interpreta claves históricas y nuevas del carrito de forma segura."""
    try:
        partes = str(clave).split(':', 1)
        producto_id = int(partes[0])
    except (TypeError, ValueError):
        return None, ''
    talla = partes[1] if len(partes) == 2 else ''
    if producto_id <= 0 or (talla and talla not in TALLAS_VALIDAS):
        return None, ''
    return producto_id, talla


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
    talla = request.POST.get('size', '').strip().upper()
    clave = _clave_linea_carrito(producto.pk, talla)

    # Se suma a la cantidad existente y se valida el total acumulado, no solo el envío actual.
    carrito = request.session.get('carrito', {})
    if not isinstance(carrito, dict):
        carrito = {}
    if producto.requires_size and talla not in TALLAS_VALIDAS:
        messages.error(request, 'Selecciona una talla válida para este producto.')
    elif not producto.requires_size and talla:
        messages.error(request, 'Este producto no requiere una talla.')
    elif cantidad <= 0:
        messages.error(request, 'Indica una cantidad válida.')
    else:
        cantidad_actual_producto = sum(
            int(valor)
            for otra_clave, valor in carrito.items()
            if _leer_clave_linea_carrito(otra_clave)[0] == producto.pk
            and str(valor).isdigit()
        )
        cantidad_actual_linea = int(carrito.get(clave, 0))
        if cantidad_actual_producto + cantidad > producto.stock:
            messages.error(request, 'La cantidad solicitada supera el stock disponible.')
        else:
            carrito[clave] = cantidad_actual_linea + cantidad
            request.session['carrito'] = carrito
            messages.success(request, f'{producto.name} se ha añadido al carrito.')

    return _redireccion_carrito(request, 'shop_home')


@require_POST
def quitar_del_carrito(request, pk):
    """Elimina por completo un producto del carrito de sesión."""
    carrito = request.session.get('carrito', {})
    talla = request.POST.get('size', '').strip().upper()
    carrito.pop(_clave_linea_carrito(pk, talla), None)
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
    talla = request.POST.get('size', '').strip().upper()
    clave = _clave_linea_carrito(producto.pk, talla)

    # Cero es una operación válida de eliminación; valores negativos o mayores al stock no.
    if producto.requires_size and talla not in TALLAS_VALIDAS:
        messages.error(request, 'La talla del carrito no es válida.')
    elif not producto.requires_size and talla:
        messages.error(request, 'Este producto no requiere una talla.')
    elif cantidad < 0:
        messages.error(request, 'Indica una cantidad válida.')
    elif cantidad == 0:
        carrito.pop(clave, None)
        request.session['carrito'] = carrito
        messages.info(request, f'{producto.name} se ha quitado del carrito.')
    elif cantidad + sum(
        int(valor)
        for otra_clave, valor in carrito.items()
        if otra_clave != clave
        and _leer_clave_linea_carrito(otra_clave)[0] == producto.pk
        and str(valor).isdigit()
    ) > producto.stock:
        messages.error(request, 'La cantidad solicitada supera el stock disponible.')
    else:
        carrito[clave] = cantidad
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
    ids_producto = {item['product'].pk for item in contexto['cart_items']}
    cantidades_por_producto = {}
    for item in contexto['cart_items']:
        producto_id = item['product'].pk
        cantidades_por_producto[producto_id] = (
            cantidades_por_producto.get(producto_id, 0) + item['quantity']
        )
    pedido = None
    stock_valido = True

    # La reserva impide vender las mismas unidades mientras Stripe procesa el pago.
    with transaction.atomic():
        # select_for_update bloquea las filas en motores que soportan bloqueo pesimista,
        # evitando que dos confirmaciones consuman simultáneamente las mismas unidades.
        productos = {
            producto.pk: producto
            for producto in Producto.objects.select_for_update().filter(pk__in=ids_producto)
        }
        if len(productos) != len(ids_producto) or any(
            productos[producto_id].stock < cantidad
            for producto_id, cantidad in cantidades_por_producto.items()
            if producto_id in productos
        ):
            stock_valido = False
        else:
            total = sum(
                (
                    productos[item['product'].pk].price * item['quantity']
                    for item in contexto['cart_items']
                ),
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
            for item in contexto['cart_items']:
                producto = productos[item['product'].pk]
                LineaPedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    nombre_producto=producto.name,
                    precio_unitario=producto.price,
                    cantidad=item['quantity'],
                    talla=item['size'],
                )
            for producto_id, cantidad in cantidades_por_producto.items():
                # La cantidad se descuenta como reserva y se repone si Stripe cancela o caduca.
                producto = productos[producto_id]
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
                'product_data': {
                    'name': (
                        f'{linea.nombre_producto} (Talla {linea.talla})'
                        if linea.talla else linea.nombre_producto
                    ),
                },
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
    # El bloqueo de fila y la transición solo desde pendiente_pago hacen idempotente el evento.
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
    # La transición protegida evita reponer stock dos veces si llega más de un aviso de Stripe.
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
    # El ID del navegador debe coincidir con la sesión guardada en el pedido antes de consultar Stripe.
    if not session_id or session_id != pedido.stripe_session_id:
        messages.error(request, 'No se pudo verificar la sesión de pago.')
        return redirect('ver_carrito')

    try:
        sesion_pago = _cliente_stripe().v1.checkout.sessions.retrieve(session_id)
    except stripe.StripeError:
        logger.exception('No se pudo consultar la sesión Stripe del pedido %s.', pedido.pk)
        messages.error(request, 'No se pudo comprobar el pago. Vuelve a intentarlo en unos instantes.')
        return redirect('ver_carrito')

    # La URL de retorno no prueba el pago; se confirma solo tras leer payment_status desde la API.
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
            # Se solicita expiración al proveedor y solo entonces se libera la reserva local.
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
    # Esta ruta excluye CSRF porque Stripe no posee token Django; la firma HMAC autentica el cuerpo.
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

    # La firma ya verificada permite usar metadata para localizar el pedido vinculado.
    sesion_pago = evento.data.object
    pedido_id = (sesion_pago.get('metadata') or {}).get('pedido_id')
    if not pedido_id:
        return HttpResponse(status=200)

    # Los eventos asíncronos terminados solo se aprueban si reportan pago efectivamente liquidado.
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
