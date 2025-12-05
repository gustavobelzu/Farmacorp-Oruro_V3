from django.db import models
from clientes.models import Cliente
from empleados.models import Empleado
from productos.models import Producto
from farmacia.models import Sucursal
from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP


class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True)
    factura = models.BooleanField(default=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="ventas")
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="ventas")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name="ventas")
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    estado = models.CharField(max_length=20, default="pendiente")

    def clean(self):
        # Validaciones a nivel de modelo
        if self.total is not None and self.total < 0:
            raise ValidationError({'total': 'El total no puede ser negativo.'})

    def save(self, *args, **kwargs):
        # Asegurar fecha aware
        if not self.fecha:
            self.fecha = timezone.now()

        # Detectar transición de estado (si ya existe en DB)
        previous_estado = None
        if self.pk:
            try:
                prev = Venta.objects.get(pk=self.pk)
                previous_estado = prev.estado
            except Venta.DoesNotExist:
                previous_estado = None

        # Quantize total to 2 decimales (evita ValidationError por decimal_places)
        if self.total is not None:
            try:
                self.total = Decimal(self.total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except Exception:
                # si por alguna razón no se puede convertir, dejar que full_clean() capture el error
                pass

        # Si estamos pasando de 'pendiente' a 'pagado' validamos stock antes de guardar
        will_mark_paid = (previous_estado == 'pendiente' and self.estado == 'pagado')
        if will_mark_paid:
            # Importar aquí para evitar dependencias circulares
            from inventario.models import Inventario
            # Verificar que hay suficiente stock para cada detalle
            for detalle in self.detalles.all():
                try:
                    inv = Inventario.objects.get(producto=detalle.producto, sucursal=self.sucursal)
                except Inventario.DoesNotExist:
                    raise ValidationError({'estado': f"No hay inventario registrado para {detalle.producto.nombre} en la sucursal."})
                if inv.cantidad < detalle.cantidad:
                    raise ValidationError({'estado': f"Stock insuficiente para {detalle.producto.nombre}: disponible {inv.cantidad}, requerido {detalle.cantidad}."})

        # Ejecutar validaciones antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)

        # Después de guardar, si hubo transición aplicar/revertir ajustes de stock
        try:
            from django.db import transaction
            from inventario.models import Inventario
            with transaction.atomic():
                # pendiente -> pagado : decrementar
                if will_mark_paid:
                    for detalle in self.detalles.all():
                        inv = Inventario.objects.select_for_update().get(producto=detalle.producto, sucursal=self.sucursal)
                        inv.cantidad = max(Decimal('0'), Decimal(inv.cantidad) - Decimal(detalle.cantidad))
                        inv.save()
                        # actualizar stock global del producto si existe
                        try:
                            prod = detalle.producto
                            prod.stock = max(0, prod.stock - detalle.cantidad)
                            prod.save()
                        except Exception:
                            pass

                # pagado -> pendiente : revertir (aumentar)
                if previous_estado == 'pagado' and self.estado == 'pendiente':
                    for detalle in self.detalles.all():
                        inv = Inventario.objects.select_for_update().get(producto=detalle.producto, sucursal=self.sucursal)
                        inv.cantidad = Decimal(inv.cantidad) + Decimal(detalle.cantidad)
                        inv.save()
                        try:
                            prod = detalle.producto
                            prod.stock = prod.stock + detalle.cantidad
                            prod.save()
                        except Exception:
                            pass
        except Exception:
            # No queremos que errores secundarios impidan el guardado de la venta;
            # Si hay un problema crítico de stock la validación previa ya habría lanzado.
            pass

    def __str__(self):
        return f"Venta {self.id_venta} - Total: {self.total}"

    def calcular_ganancia(self):
        return self.detalles.aggregate(
            total=Coalesce(Sum("ganancia"), Value(0), output_field=DecimalField())
        )["total"] or Decimal(0)

    def actualizar_total_db(self):
        """Recalcula el total de la venta y actualiza la columna en la DB sin re-validar la instancia."""
        total = self.detalles.aggregate(total=Coalesce(Sum('subtotal'), Value(0), output_field=DecimalField()))['total'] or Decimal('0.00')
        # Quantize the aggregated total to 2 decimals to respect DecimalField(decimal_places=2)
        try:
            total = Decimal(total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            total = Decimal('0.00')
        # Actualizar directamente en la base de datos para evitar bucles de save
        Venta.objects.filter(pk=self.pk).update(total=total)



class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="detalles_ventas",max_length=30)
    cantidad = models.IntegerField(validators=[MinValueValidator(1)])
    descuento = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))])
    iva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    metodo_pago = models.CharField(
        max_length=20,
        choices=[
            ("efectivo", "Efectivo"),
            ("tarjeta", "Tarjeta"),
            ("transferencia", "Transferencia"),
        ],
        default="efectivo")
    ganancia = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))


    from decimal import Decimal

    def clean(self):
        if self.cantidad is None or self.cantidad < 1:
            raise ValidationError({'cantidad': 'La cantidad debe ser al menos 1.'})
        if self.precio_unitario is None or self.precio_unitario < 0:
            raise ValidationError({'precio_unitario': 'El precio unitario no puede ser negativo.'})
        if self.descuento < 0 or self.descuento > 100:
            raise ValidationError({'descuento': 'El descuento debe estar entre 0 y 100.'})
        if self.iva < 0 or self.iva > 100:
            raise ValidationError({'iva': 'El IVA debe estar entre 0 y 100.'})

    def save(self, *args, **kwargs):
        # Normalizar valores como Decimals y quantize a 2 decimales
        descuento = Decimal(self.descuento or 0)
        cantidad = Decimal(self.cantidad or 0)
        precio_unitario = Decimal(self.precio_unitario or 0)

        # Quantize precio_unitario a 2 decimales
        precio_unitario = precio_unitario.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.precio_unitario = precio_unitario

        # Calcular subtotal: aplicar descuento primero
        subtotal = (precio_unitario * cantidad) * (Decimal('1') - (descuento / Decimal('100')))
        # Quantize subtotal a 2 decimales
        subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.subtotal = subtotal

        # Obtener precio de compra actual (si existe)
        ultima_compra = getattr(self.producto, 'compras', None)
        precio_compra = Decimal(0)
        if ultima_compra is not None:
            ultima = ultima_compra.order_by("-fecha_compra").first()
            precio_compra = Decimal(getattr(ultima, 'precio_compra', 0) or 0)

        # Calcular ganancia como Decimal y quantize a 2 decimales
        ganancia = (precio_unitario - precio_compra) * cantidad
        ganancia = ganancia.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.ganancia = ganancia

        # Ejecutar validaciones (ahora que precios/subtotal/ganancia están normalizados)
        self.full_clean()

        super().save(*args, **kwargs)

        # Actualizar total de la venta asociado (actualización directa en DB)
        try:
            if self.venta_id:
                self.venta.actualizar_total_db()
        except Exception:
            # No queremos que errores secundarios impidan el guardado del detalle
            pass


    def __str__(self):
        return f"Detalle de {self.venta} - {self.producto}"