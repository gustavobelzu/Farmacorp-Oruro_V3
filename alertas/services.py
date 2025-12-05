# alertas/services.py
from datetime import datetime, timedelta, date
from django.utils import timezone
from inventario.models import Inventario
from productos.models import Producto
from .models import Alerta

def generar_alertas():
    hoy = date.today()
    limite_vencimiento = hoy + timedelta(days=30)

    # Stock bajo por inventario
    for inv in Inventario.objects.select_related("producto", "sucursal"):
        if inv.cantidad <= inv.stock_minimo:
            Alerta.objects.get_or_create(
                producto=inv.producto,
                tipo="Stock Bajo",
                defaults={"descripcion": f"Producto {inv.producto.nombre} en sucursal {inv.sucursal.nombre} tiene {inv.cantidad} unidades"}
            )

    # Vencimiento próximo
    for prod in Producto.objects.filter(fecha_vencimiento__lte=limite_vencimiento):
        Alerta.objects.get_or_create(
            producto=prod,
            tipo="Vencimiento Próximo",
            defaults={"descripcion": f"Producto {prod.nombre} vence el {prod.fecha_vencimiento}"}
        )

    # Medicamentos de alto riesgo (ejemplo: tag o nombre)
    alto_riesgo_qs = Producto.objects.filter(nombre__icontains="morfina")  # ej.
    for prod in alto_riesgo_qs:
        Alerta.objects.get_or_create(
            producto=prod,
            tipo="Alto Riesgo",
            defaults={"descripcion": f"Producto {prod.nombre} catalogado como alto riesgo."}
        )
