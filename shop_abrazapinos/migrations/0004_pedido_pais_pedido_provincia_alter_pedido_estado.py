# Completa la dirección postal y registra las opciones visibles para gestionar estados.
# provincia usa cadena vacía como valor de compatibilidad para pedidos históricos.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop_abrazapinos', '0003_pedido_lineapedido'),
    ]

    operations = [
        # El país tiene un valor inicial útil para pedidos existentes y nuevos formularios.
        migrations.AddField(
            model_name='pedido',
            name='pais',
            field=models.CharField(default='España', max_length=80),
        ),
        # La provincia histórica queda vacía; el formulario de checkout la valida como obligatoria.
        migrations.AddField(
            model_name='pedido',
            name='provincia',
            field=models.CharField(default='', max_length=120),
        ),
        # Define las etiquetas traducidas disponibles al administrar el estado del pedido.
        migrations.AlterField(
            model_name='pedido',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('preparando', 'En preparación'), ('enviado', 'Enviado'), ('completado', 'Completado'), ('cancelado', 'Cancelado')], default='pendiente', max_length=20),
        ),
    ]
