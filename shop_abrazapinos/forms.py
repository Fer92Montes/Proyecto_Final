"""Formularios para completar los datos de entrega y pago del pedido."""

from django import forms

from .models import Pedido, Producto


class FormularioProducto(forms.ModelForm):
    """Formulario de catálogo para crear y actualizar productos desde la tienda."""

    class Meta:
        model = Producto
        fields = ('name', 'description', 'price', 'stock', 'image', 'requires_size')
        labels = {
            'name': 'Nombre del producto',
            'description': 'Descripción',
            'price': 'Precio (€)',
            'stock': 'Cantidad disponible',
            'image': 'Imagen del producto',
            'requires_size': 'Requiere seleccionar talla',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'price': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'min': '0', 'step': '1'}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }


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