from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, UpdateView
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
import json

from .models import Inventario
from .forms import InventarioForm
from productos.models import Producto
from farmacia.models import Sucursal


# LISTA DE INVENTARIO
@method_decorator(login_required, name="dispatch")
class InventarioListView(ListView):
    model = Inventario
    template_name = "inventario/list.html"
    context_object_name = "inventarios"
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.rol not in ['administrador', 'encargado_almacen']:
            messages.error(request, "No tienes permiso para acceder al inventario.")
            return redirect('usuario:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar sucursales para el filtro
        context['sucursales'] = Sucursal.objects.all()
        return context


# EDITAR INVENTARIO (CBV)
@method_decorator(login_required, name="dispatch")
class InventarioUpdateView(UpdateView):
    model = Inventario
    form_class = InventarioForm
    template_name = "inventario/form.html"
    success_url = "/inventario/"

    def dispatch(self, request, *args, **kwargs):
        if request.user.rol not in ['administrador', 'encargado_almacen']:
            messages.error(request, "No tienes permiso para editar el inventario.")
            return redirect('usuario:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Inventario actualizado correctamente.")
        return super().form_valid(form)


# CREAR INVENTARIO (FBV)
@login_required
def inventario_create(request):
    if request.user.rol not in ['administrador', 'encargado_almacen']:
        messages.error(request, "No tienes permiso para crear inventario.")
        return redirect('usuario:dashboard')
    
    form = InventarioForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Inventario creado exitosamente.")
        return redirect("inventario:list")
    return render(request, "inventario/form.html", {"form": form})


# ACTUALIZAR INVENTARIO (FBV)
@login_required
def inventario_update(request, pk):
    if request.user.rol not in ['administrador', 'encargado_almacen']:
        messages.error(request, "No tienes permiso para actualizar inventario.")
        return redirect('usuario:dashboard')
    
    inventario = get_object_or_404(Inventario, pk=pk)
    form = InventarioForm(request.POST or None, instance=inventario)
    if form.is_valid():
        form.save()
        messages.success(request, "Inventario actualizado exitosamente.")
        return redirect("inventario:list")
    return render(request, "inventario/form.html", {"form": form})


# ELIMINAR INVENTARIO
@login_required
def inventario_delete(request, pk):
    if request.user.rol not in ['administrador', 'encargado_almacen']:
        messages.error(request, "No tienes permiso para eliminar inventario.")
        return redirect('usuario:dashboard')
    
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == "POST":
        inventario.delete()
        messages.success(request, "Inventario eliminado correctamente.")
        return redirect("inventario:list")
    return render(request, "inventario/delete.html", {"inventario": inventario})


# API: ACTUALIZAR STOCK DESDE DASHBOARD O AJAX
@csrf_exempt
@require_POST
def actualizar_stock(request):
    """
    API que recibe un JSON con { "id_inventario": int, "cantidad": int }
    y actualiza el stock de ese inventario.
    """
    # Verificar permisos
    if not request.user.is_authenticated or request.user.rol not in ['administrador', 'encargado_almacen']:
        return JsonResponse({"ok": False, "error": "No tienes permiso para actualizar el stock."}, status=403)
    
    try:
        data = json.loads(request.body)
        inv = Inventario.objects.get(pk=data["id_inventario"])
        inv.cantidad = int(data["cantidad"])
        inv.save()

        return JsonResponse({
            "ok": True,
            "id_inventario": inv.id_inventario,
            "cantidad": inv.cantidad,
            "mensaje": f"Stock actualizado para {inv.producto.nombre}"
        })

    except Inventario.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Inventario no encontrado."}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
