from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Proveedor,Compra
from .forms import ProductoForm, ProveedorForm,CompraForm
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from inventario.models import Inventario
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Avg
import datetime

#crud de productos
@login_required
def producto_list(request):
    if request.user.rol not in ['administrador', 'encargado_almacen', 'farmaceutico']:
        messages.error(request, "No tienes permiso para acceder a la lista de productos.")
        return redirect('usuario:dashboard')

    # QuerySet base
    productos_qs = Producto.objects.select_related('proveedor').all().order_by('nombre')

    # Paginación (permite ?page= y ?per_page=)
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
    except (TypeError, ValueError):
        per_page = 10

    paginator = Paginator(productos_qs, per_page)
    try:
        productos = paginator.page(page)
    except PageNotAnInteger:
        productos = paginator.page(1)
    except EmptyPage:
        productos = paginator.page(paginator.num_pages)

    # Estadísticas para las cards
    total_productos = productos_qs.count()
    productos_stock_bajo = productos_qs.filter(stock__lt=10).count()
    hoy = timezone.now().date()
    productos_por_vencer = productos_qs.filter(fecha_vencimiento__isnull=False, fecha_vencimiento__lte=hoy + datetime.timedelta(days=30)).count()
    valor_total = productos_qs.aggregate(
        total=Sum(ExpressionWrapper(F('precio_unitario') * F('stock'), output_field=DecimalField(max_digits=20, decimal_places=2)))
    )['total'] or 0

    proveedores = Proveedor.objects.all()

    context = {
        'productos': productos,
        'proveedores': proveedores,
        'total_productos': total_productos,
        'productos_stock_bajo': productos_stock_bajo,
        'productos_por_vencer': productos_por_vencer,
        'valor_total': valor_total,
    }
    return render(request, "productos/list.html", context)

@login_required
def producto_create(request):
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("productos:list")
    else:
        form = ProductoForm()
    return render(request, "productos/form.html", {"form": form})

@login_required
def producto_update(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect("productos:list")
    else:
        form = ProductoForm(instance=producto)
    return render(request, "productos/form.html", {"form": form})

@login_required
def producto_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    try:
        producto.delete()
        messages.success(request, "Producto eliminado correctamente.")
    except ProtectedError:
        messages.error(request, "No se puede eliminar: existen compras asociadas a este producto.")
    return redirect("productos:list")

#crud de proveedores
def proveedor_list(request):
    proveedores = Proveedor.objects.all()
    if request.user.rol not in ['administrador']:
        messages.error(request, "No tienes permiso para acceder a la lista de proveedores.")
        return redirect('usuario:dashboard')
    else:
        return render(request, "proveedores/listp.html", {"proveedores": proveedores})

def proveedor_create(request):
    form = ProveedorForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("productos:listp")
    return render(request, "proveedores/form.html", {"form": form})

def proveedor_update(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorForm(request.POST or None, instance=proveedor)
    if form.is_valid():
        form.save()
        return redirect("productos:listp")
    return render(request, "proveedores/form.html", {"form": form})

def proveedor_delete(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        proveedor.delete()
        return redirect("productos:listp")
    return render(request, "proveedores/delete.html", {"proveedor": proveedor})
 #Requerimiento f8
 
class ProductoDetailView(DetailView):
    model = Producto
    template_name = 'productos/detalle.html'
    context_object_name = 'producto'
    pk_url_kwarg = 'codigo_barras'


def producto_detail(request, codigo):
    producto = get_object_or_404(Producto, codigo_barras=codigo)
    # sustitutos: productos con nombre similar o campo generico si existe
    sustitutos = Producto.objects.filter(nombre__icontains=producto.nombre.split()[0]).exclude(pk=producto.pk)[:5]
    return render(request, 'productos/detalle.html', {'producto':producto, 'sustitutos':sustitutos})
# Compra CRUD
def compra_list(request):
    if request.user.rol not in ['administrador', 'encargado_almacen']:
        messages.error(request, "No tienes permiso para acceder a la lista de compras.")
        return redirect('usuario:dashboard')
    else:
        compras_qs = Compra.objects.select_related("producto").all()

        # Aggregados para las cards
        total_invertido = compras_qs.aggregate(
            total=Sum(ExpressionWrapper(F('precio_compra') * F('cantidad'), output_field=DecimalField(max_digits=20, decimal_places=2)))
        )['total'] or 0

        total_productos = compras_qs.aggregate(total=Sum('cantidad'))['total'] or 0

        promedio_compra = compras_qs.aggregate(
            avg=Avg(ExpressionWrapper(F('precio_compra') * F('cantidad'), output_field=DecimalField(max_digits=20, decimal_places=2)))
        )['avg'] or 0

        context = {
            'compras': compras_qs,
            'total_invertido': total_invertido,
            'total_productos': total_productos,
            'promedio_compra': promedio_compra,
        }
        return render(request, "compras/listc.html", context)

def compra_create(request):
    form = CompraForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Compra registrada correctamente.")
        return redirect("productos:listc")
    return render(request, "compras/form.html", {"form": form})

def compra_update(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    form = CompraForm(request.POST or None, instance=compra)
    if form.is_valid():
        form.save()
        messages.success(request, "Compra actualizada correctamente.")
        return redirect("productos:listc")
    return render(request, "compras/form.html", {"form": form})

def compra_delete(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    if request.method == "POST":
        compra.delete()
        messages.success(request, "Compra eliminada correctamente.")
        return redirect("productos:listc")
    return render(request, "compras/delete.html", {"compra": compra})
