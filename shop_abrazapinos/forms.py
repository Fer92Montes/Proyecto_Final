"""Formularios para completar los datos de entrega y pago del pedido."""

from django import forms

from .models import Pedido


class FormularioTramitarPedido(forms.Form):
    """Valida los datos de envío y el método de pago preferido del cliente."""

    # Los límites de longitud replican el esquema persistido; autocomplete ayuda
    # al navegador a proponer datos conocidos para la dirección de entrega.
    destinatario = forms.CharField(
        label='Nombre del destinatario',
        max_length=120,
        widget=forms.TextInput(attrs={'autocomplete': 'name'}),
    )
    direccion = forms.CharField(
        label='Dirección',
        max_length=255,
        widget=forms.TextInput(attrs={'autocomplete': 'street-address'}),
    )
    ciudad = forms.CharField(
        label='Ciudad o municipio',
        max_length=120,
        widget=forms.TextInput(attrs={'autocomplete': 'address-level2'}),
    )
    provincia = forms.CharField(
        label='Provincia',
        max_length=120,
        widget=forms.TextInput(attrs={'autocomplete': 'address-level1'}),
    )
    codigo_postal = forms.CharField(
        label='Código postal',
        max_length=20,
        widget=forms.TextInput(attrs={'autocomplete': 'postal-code'}),
    )
    pais = forms.CharField(
        label='País',
        max_length=80,
        initial='España',
        widget=forms.TextInput(attrs={'autocomplete': 'country-name'}),
    )
    telefono = forms.CharField(
        label='Teléfono de contacto (opcional)',
        max_length=30,
        required=False,
        widget=forms.TelInput(attrs={'autocomplete': 'tel'}),
    )
    # Las opciones proceden del modelo para mantener una única lista permitida.
    metodo_pago = forms.ChoiceField(
        label='Método de pago preferido',
        choices=Pedido.METODOS_PAGO,
        initial='stripe',
        widget=forms.HiddenInput,
    )