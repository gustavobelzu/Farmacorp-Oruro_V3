from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum
from .models import Cliente
from .forms import ClienteForm
from ventas.models import Venta


#  Listar todos los clientes
@login_required
def cliente_list(request):
    if request.user.rol == 'administrador' or request.user.rol == 'farmaceutico':
        clientes = Cliente.objects.all().order_by("nombre")
        return render(request, "clientes/list.html", {"clientes": clientes})
    else:
        messages.error(request, "No tiene permisos para ver clientes")
        return redirect('usuario:dashboard')


#  Crear un cliente
@login_required
def cliente_create(request):
    form = ClienteForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("clientes:list")
    return render(request, "clientes/form.html", {"form": form})


#  Editar un cliente
@login_required
def cliente_update(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    form = ClienteForm(request.POST or None, instance=cliente)
    if form.is_valid():
        form.save()
        return redirect("clientes:list")
    return render(request, "clientes/form.html", {"form": form})


#  Eliminar un cliente
@login_required
def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        cliente.delete()
        return redirect("clientes:list")
    return render(request, "clientes/delete.html", {"cliente": cliente})


#  Ver historial de compras y recetas de un cliente
@login_required
def historial_cliente(request, ci_cliente=None):
    # Si no se proporciona ci_cliente, intentar obtenerlo de GET
    if not ci_cliente:
        ci_cliente = request.GET.get('ci_cliente')
        if not ci_cliente:
            return redirect('clientes:list')
    
    cliente = get_object_or_404(Cliente, ci_cliente=ci_cliente)

    # Obtener ventas con detalles
    ventas = (cliente.ventas.select_related("sucursal", "empleado")
             .prefetch_related("detalles", "detalles__producto")
             .order_by("-fecha"))

    # Obtener recetas
    recetas = cliente.recetas.select_related("empleado").order_by("-fecha_emision")

    # Calcular estadísticas
    total_gastado = ventas.aggregate(total=Sum("total"))["total"] or 0
    total_productos = sum(v.detalles.aggregate(total=Sum("cantidad"))["total"] or 0 for v in ventas)
    productos_frecuentes = (
        cliente.ventas.values("detalles__producto__nombre")
        .annotate(total=Sum("detalles__cantidad"))
        .order_by("-total")[:5]
    )

    # Agrupar ventas por mes para gráfico
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    ventas_por_mes = (
        ventas.annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(total=Sum('total'))
        .order_by('mes')
    )

    return render(request, "clientes/historial.html", {
        "cliente": cliente,
        "ventas": ventas,
        "recetas": recetas,
        "total_gastado": total_gastado,
        "total_productos": total_productos,
        "productos_frecuentes": productos_frecuentes,
        "ventas_por_mes": list(ventas_por_mes),
    })


# API: Clientes con más compras (para dashboard o reportes)
@login_required
def api_clientes_top(request):
    """
    Devuelve los clientes que más han comprado (para usar con Chart.js u otros gráficos)
    """
    data = (
        Venta.objects.values("cliente__nombre")
        .annotate(total_gastado=Sum("total"))
        .order_by("-total_gastado")[:5]
    )

    labels = [d["cliente__nombre"] for d in data]
    values = [float(d["total_gastado"]) for d in data]

    return JsonResponse({"labels": labels, "values": values})
