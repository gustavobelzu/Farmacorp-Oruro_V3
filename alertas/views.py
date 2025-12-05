# alertas/views.py
from django.shortcuts import redirect, render
from django.utils.timezone import now, timedelta
from django.db.models import F
from django.http import JsonResponse
from productos.models import Producto
from .models import Alerta
import json
from django.contrib import messages


def generar_alertas():
    """Genera alertas automáticas por stock bajo, vencimiento cercano y alto riesgo."""
    hoy = now().date()
    hoy.strftime("%d/%m/%Y %H:%M")
    # ALERTA 1: Stock bajo
    bajos = Producto.objects.filter(stock__lte=6)  
    for p in bajos:
        Alerta.objects.get_or_create(
            producto=p,
            tipo="Stock Bajo",
            descripcion=f"El producto {p.nombre} tiene stock bajo ({p.stock} unidades)",
            estado=True
        )

    #ALERTA 2: Vencimiento cercano (30 días)
    proximos = Producto.objects.filter(fecha_vencimiento__lte=hoy + timedelta(days=30))
    for p in proximos:
        Alerta.objects.get_or_create(
            producto=p,
            tipo="Vencimiento Próximo",
            descripcion=f"El producto {p.nombre} vence el {p.fecha_vencimiento}",
            estado=True
        )

    # ALERTA 3: Producto de alto riesgo (palabra clave)
    riesgos = Producto.objects.filter(descripcion__icontains="controlado")
    for p in riesgos:
        Alerta.objects.get_or_create(
            producto=p,
            tipo="Alto Riesgo",
            descripcion=f"El producto {p.nombre} es de alto riesgo (controlado)",
            estado=True
        )


def lista_alertas(request):
    """Vista HTML que muestra todas las alertas actuales."""
    generar_alertas()  # Actualiza las alertas antes de mostrar
    alertas = Alerta.objects.all().order_by("-fecha_alerta")
    if request.user.rol != 'administrador' and request.user.rol != 'farmaceutico' and request.user.rol != 'encargado_almacen':
        messages.error(request, "No tiene permisos para ver alertas")
        return redirect('usuario:dashboard')
    return render(request, "alertas/list.html", {"alertas": alertas})


def api_alertas(request):
    """API para el navbar (notificaciones con campana)."""
    alertas = Alerta.objects.filter(estado=True).order_by("-fecha_alerta")[:5]
    data = [
        {
            "tipo": a.tipo,
            "descripcion": a.descripcion,
            "producto": a.producto.nombre,
        }
        for a in alertas
    ]
    return JsonResponse({"alertas": data, "count": len(data)})
