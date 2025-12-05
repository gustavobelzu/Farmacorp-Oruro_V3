from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.generic import DetailView
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Sum,Count
from django.contrib import messages
from decimal import Decimal
import json
from empleados import models
from .models import Venta, DetalleVenta
from .forms import VentaForm
from productos.models import Producto
from clientes.models import Cliente
from empleados.models import Empleado
from farmacia.models import Sucursal
from inventario.models import Inventario
from decimal import Decimal

# FUNCIONES AUXILIARES


def calcular_subtotal(cantidad, precio_unitario, descuento=0, iva=0):
    """Calcula subtotal con descuento e IVA"""
    bruto = cantidad * precio_unitario
    descuento_val = bruto * (descuento / 100)
    iva_val = (bruto - descuento_val) * (iva / 100)
    return bruto - descuento_val + iva_val

def buscar_clientes(request):
    query = request.GET.get("q", "")
    resultados = Cliente.objects.filter(ci_cliente__icontains=query)[:10]
    data = [{"id": c.id, "ci": c.ci_cliente, "nombre": c.nombre} for c in resultados]
    return JsonResponse(data, safe=False)

# CRUD DE VENTAS


@login_required
def venta_list(request):
    """Lista todas las ventas registradas con filtros y paginación"""
    # Filtros
    estado = request.GET.get('estado')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    sucursal = request.GET.get('sucursal')
    
    # Query base con optimización de consultas
    ventas = Venta.objects.select_related(
        "cliente", 
        "empleado", 
        "sucursal"
    ).prefetch_related(
        'detalles',
        'detalles__producto'
    )
    
    # Aplicar filtros
    if estado:
        ventas = ventas.filter(estado=estado)
    if fecha_inicio:
        ventas = ventas.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha__lte=fecha_fin)
    if sucursal:
        ventas = ventas.filter(sucursal_id=sucursal)
        
    # Ordenamiento
    order_by = request.GET.get('order_by', '-fecha')
    ventas = ventas.order_by(order_by)
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(ventas, 25)  # 25 ventas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas básicas
    total_ventas = ventas.aggregate(
    total=Sum('total'),
    count=Count('id_venta')
    )

    
    context = {
        "page_obj": page_obj,
        "ventas": page_obj, 
        "total_ventas": total_ventas['total'],
        "num_ventas": total_ventas['count'],
        "sucursales": Sucursal.objects.all()
    }
    if request.user.rol == 'administrador' or request.user.rol == 'farmaceutico':
        return render(request, "ventas/list.html", context)
    else:
        messages.error(request, "No tiene permisos para ver ventas")
        return redirect('usuario:dashboard')
        


@login_required
def venta_update(request, pk):
    """Editar una venta"""
    venta = get_object_or_404(Venta, pk=pk)
    form = VentaForm(request.POST or None, instance=venta)
    if form.is_valid():
        form.save()
        messages.success(request, "Venta actualizada correctamente.")
        return redirect("ventas:venta_list")
    return render(request, "ventas/form.html", {"form": form})


@login_required
def venta_delete(request, pk):
    """Eliminar una venta"""
    venta = get_object_or_404(Venta, pk=pk)
    if request.method == "POST":
        venta.delete()
        messages.success(request, "Venta eliminada correctamente.")
        return redirect("ventas:venta_list")
    return render(request, "ventas/delete.html", {"venta": venta})


# POS Y CREACIÓN DE VENTAS

from django.core.cache import cache
from datetime import timedelta

@login_required
def pos(request):
    """Vista principal del punto de venta con caché de productos frecuentes"""
    # Obtener el empleado del usuario autenticado
    try:
        empleado_actual = request.user.ci_empleado
        if not empleado_actual:
            raise Empleado.DoesNotExist
        # Cargar la sucursal relacionada
        sucursal_actual = empleado_actual.sucursal
    except Empleado.DoesNotExist:
        messages.error(request, "No se encontró un empleado asociado a tu usuario")
        return redirect('usuario:dashboard')
    
    # Obtener productos del caché o DB
    cache_key = 'productos_frecuentes'
    productos_frecuentes = cache.get(cache_key)
    
    if productos_frecuentes is None:
        # Calcular productos más vendidos en los últimos 30 días
        from django.utils import timezone
        from django.db.models import Count
        
        fecha_limite = timezone.now() - timedelta(days=30)
        productos_frecuentes = Producto.objects.filter(
            detalles_ventas__venta__fecha__gte=fecha_limite
        ).annotate(
            ventas_count=Count('detalles_ventas')
        ).order_by('-ventas_count')[:50]
        
        # Guardar en caché por 12 horas
        cache.set(cache_key, productos_frecuentes, timeout=43200)
    
    # Obtener todos los productos para búsqueda
    productos = Producto.objects.all()

    
    # Optimizar consultas relacionadas
    clientes = Cliente.objects.all()
    
    return render(request, "ventas/venta_pos.html", {
        "productos": productos,
        "productos_frecuentes": productos_frecuentes,
        "clientes": clientes,
        "empleado_actual": empleado_actual,
        "sucursal_actual": sucursal_actual
    })


@login_required
@transaction.atomic
def crear_venta(request):
    if request.method == "POST":
        try:
            # Validar datos requeridos
            required_fields = ['empleado', 'sucursal', 'cliente_manual']
            for field in required_fields:
                if not request.POST.get(field):
                    raise ValueError(f"El campo {field} es requerido")

            # Obtener y validar datos del cliente
            ci_cliente = request.POST.get("cliente_manual")
            cliente = Cliente.objects.filter(ci_cliente=ci_cliente).first()

            if not cliente:
                messages.warning(request, "Cliente no encontrado. Redirigiendo al registro de clientes.")
                return redirect(f"{reverse('clientes:create')}?ci={ci_cliente}")

            # Obtener empleado y sucursal del usuario autenticado
            empleado = request.user.ci_empleado
            if not empleado:
                raise ValueError("No se encontró un empleado asociado a tu usuario")
            sucursal = empleado.sucursal


            # Crear venta
            venta = Venta.objects.create(
                cliente=cliente,
                empleado=empleado,
                sucursal=sucursal,
                estado="pendiente"
            )

            # Procesar detalles de la venta
            total = Decimal('0.0')
            productos = request.POST.getlist("producto")
            cantidades = request.POST.getlist("cantidad")
            descuentos = request.POST.getlist("descuento")

            if not productos:
                raise ValueError("No se han especificado productos para la venta")

            for i in range(len(productos)):
                try:
                    # Obtener datos del producto
                    producto = Producto.objects.get(codigo_barras=productos[i])
                    cantidad = int(cantidades[i])
                    descuento = Decimal(descuentos[i] or '0')
                    if descuento < 0 or descuento > 100:
                        raise ValueError(f"Descuento inválido para el producto {producto.nombre}")
                    # Verificar stock
                    inventario = Inventario.objects.get(producto=producto, sucursal=sucursal)
                    if inventario.cantidad < cantidad:
                        raise ValueError(f"Stock insuficiente para {producto.nombre}")

                    # Calcular precios
                    precio_base = Decimal(producto.precio_unitario)
                    precio = precio_base * Decimal('1.10')  # 10% de margen
                    subtotal = precio * Decimal(cantidad) * (Decimal('1') - descuento / Decimal('100'))

                    # Crear detalle de venta
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        descuento=descuento,
                        precio_unitario=precio,
                        subtotal=subtotal,
                        metodo_pago="efectivo"  # Por defecto
                    )

                    # Nota: no actualizamos inventario/stock aquí para evitar
                    # duplicar la reducción. La clase Venta.save() ya maneja
                    # el decremento de `Inventario.cantidad` y `Producto.stock`
                    # cuando la venta pasa de 'pendiente' a 'pagado'. Mantener
                    # la lógica centralizada en el modelo evita efectos
                    # de doble descuento (vista + modelo).

                    total += subtotal

                except Producto.DoesNotExist:
                    raise ValueError(f"Producto con código {productos[i]} no encontrado")
                except Inventario.DoesNotExist:
                    raise ValueError(f"No hay inventario para el producto {producto.nombre} en la sucursal seleccionada")

            # Finalizar venta
            venta.total = total
            venta.estado = "pagado"
            venta.save()

            messages.success(request, f"Venta #{venta.id_venta} registrada correctamente")
            return redirect("ventas:venta_recibo", pk=venta.id_venta)

        except ValueError as e:
            messages.error(request, str(e))
            return redirect("ventas:venta_pos")
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")
            return redirect("ventas:venta_pos")

    return redirect("ventas:venta_pos")




# API - VERIFICACIÓN DE TOTAL


@csrf_exempt
def api_verificar_total(request):
    """
    Verifica el total calculado desde el cliente.
    Espera JSON con formato:
    {
      "items": [
        {"codigo": "123", "cantidad": 2, "descuento": 10}
      ]
    }
    """
    try:
        data = json.loads(request.body)
        items = data.get("items", [])
        total = Decimal(0)

        for it in items:
            prod = Producto.objects.get(codigo_barras=it["codigo"])
            qty = Decimal(it["cantidad"])
            descuento = Decimal(it.get("descuento", 0))
            subtotal = prod.precio_unitario * qty * (Decimal('1') - descuento / Decimal('100'))
            total += subtotal

        return JsonResponse({"ok": True, "total": str(total)})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)



# DETALLE DE VENTA Y PAGOS


@login_required
def detalle_venta(request, pk):
    """Muestra el detalle completo de una venta"""
    venta = get_object_or_404(Venta, pk=pk)
    detalles = venta.detalles.all()
    return render(request, "ventas/Detalle.html", {
        "venta": venta,
        "detalles": detalles
    })


# RECIBO Y VALIDACIÓN

class ReciboExtendidoView(DetailView):
    model = Venta
    template_name = 'ventas/recibo_extendido.html'
    context_object_name = 'venta'
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['detalles'] = self.object.detalles.all()
        context['total'] = sum(d.subtotal for d in context['detalles'])
        
        return context


@login_required
def validar_venta(request, pk):
    """Valida que el total calculado coincida con el registrado"""
    venta = get_object_or_404(Venta, id_venta=pk)
    detalles = DetalleVenta.objects.filter(venta=venta)
    total_calculado = sum(
        Decimal(d.cantidad) * Decimal(d.precio_unitario) for d in detalles
    )
    return render(request, "ventas/recibo_extendido.html", {
        "venta": venta,
        "detalles": detalles,
        "total_calculado": total_calculado
    })
