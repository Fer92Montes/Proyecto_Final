# Migración inicial de pedidos: crea cabecera de entrega y detalle de productos.
# Los nombres y precios de línea se guardan como instantánea del momento de compra.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop_abrazapinos', '0002_rename_product_producto'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # La cabecera queda asociada a un usuario existente y retiene los datos de compra.
        migrations.CreateModel(
            name='Pedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('destinatario', models.CharField(max_length=120)),
                ('direccion', models.CharField(max_length=255)),
                ('ciudad', models.CharField(max_length=120)),
                ('codigo_postal', models.CharField(max_length=20)),
                ('telefono', models.CharField(blank=True, max_length=30)),
                ('metodo_pago', models.CharField(choices=[('tarjeta', 'Tarjeta'), ('transferencia', 'Transferencia bancaria'), ('contra_reembolso', 'Pago al recibir')], max_length=24)),
                ('total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('estado', models.CharField(default='pendiente', max_length=20)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pedidos_tienda', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-creado_en'],
            },
        ),
        # Las líneas dependen del pedido, pero protegen el producto frente a borrados.
        migrations.CreateModel(
            name='LineaPedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_producto', models.CharField(max_length=200)),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=8)),
                ('cantidad', models.PositiveIntegerField()),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='shop_abrazapinos.producto')),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lineas', to='shop_abrazapinos.pedido')),
            ],
        ),
    ]
