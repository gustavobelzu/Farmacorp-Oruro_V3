from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Receta, DetalleReceta
from .forms import RecetaForm, DetalleRecetaForm, DetalleRecetaFormSet
from datetime import date

@login_required
def receta_list(request):
    """Vista para listar recetas según el rol del usuario"""
    if request.user.rol == 'cliente':
        # Cliente ve solo sus recetas
        recetas = Receta.objects.filter(
            cliente=request.user.ci_cliente
        ).prefetch_related('detalles', 'detalles__producto').order_by('-fecha_emision')
    elif request.user.rol in ['farmaceutico', 'administrador']:
        # Personal de farmacia ve todas las recetas
        recetas = Receta.objects.all().prefetch_related(
            'detalles', 'detalles__producto', 'cliente', 'empleado'
        ).order_by('-fecha_emision')
    else:
        messages.error(request, "No tiene permisos para ver recetas")
        return redirect('usuario:dashboard')

    context = {
        'recetas': recetas,
        'es_cliente': request.user.rol == 'cliente'
    }
    return render(request, "recetas/list.html", context)

@login_required
def mis_recetas(request):
    """Vista específica para que los clientes vean sus recetas"""
    if request.user.rol != 'cliente':
        messages.error(request, "Esta página es solo para clientes")
        return redirect('home')

    recetas = Receta.objects.filter(
        cliente=request.user.ci_cliente
    ).prefetch_related('detalles', 'detalles__producto').order_by('-fecha_emision')

    # Separar recetas activas e inactivas
    hoy = date.today()
    recetas_activas = []
    recetas_pasadas = []

    for receta in recetas:
        # Consideramos una receta activa si tiene menos de 30 días
        dias_pasados = (hoy - receta.fecha_emision).days
        if dias_pasados <= 30:
            recetas_activas.append(receta)
        else:
            recetas_pasadas.append(receta)

    context = {
        'recetas_activas': recetas_activas,
        'recetas_pasadas': recetas_pasadas,
        'total_recetas': len(recetas),
        'recetas_vigentes': len(recetas_activas)
    }
    return render(request, "recetas/mis_recetas.html", context)

@login_required
def receta_detalle(request, pk):
    """Vista detallada de una receta"""
    receta = get_object_or_404(Receta, pk=pk)
    
    # Verificar permisos
    if request.user.rol == 'cliente' and receta.cliente != request.user.ci_cliente:
        messages.error(request, "No tiene permiso para ver esta receta")
        return redirect('recetas:mis_recetas')

    detalles = receta.detalles.select_related('producto').all()
    
    # Calcular días de vigencia (receta válida por 30 días)
    dias_desde_emision = (date.today() - receta.fecha_emision).days
    dias_restantes = 30 - dias_desde_emision
    
    context = {
        'receta': receta,
        'detalles': detalles,
        'es_cliente': request.user.rol == 'cliente',
        'dias_restantes': dias_restantes,
        'es_vigente': dias_restantes > 0,
        'dias_vencidos': abs(dias_restantes) if dias_restantes <= 0 else 0
    }
    return render(request, "recetas/detalle.html", context)

@login_required
def receta_create(request):
    """Crear nueva receta con detalles en una sola página (solo personal autorizado)"""
    if request.user.rol not in ['farmaceutico', 'administrador']:
        messages.error(request, "No tiene permisos para crear recetas")
        return redirect('recetas:list')

    if request.method == "POST":
        form = RecetaForm(request.POST)
        formset = DetalleRecetaFormSet(request.POST, instance=None)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                receta = form.save(commit=False)
                receta.empleado = request.user.ci_empleado
                receta.save()
                
                # Guardar los detalles (solo si hay al menos uno)
                formset.instance = receta
                formset.save()
            
            messages.success(request, "Receta creada exitosamente con todos sus medicamentos")
            return redirect('recetas:detalle', pk=receta.pk)
        else:
            if formset.errors:
                messages.error(request, "Por favor corrija los errores en los medicamentos")
    else:
        form = RecetaForm()
        formset = DetalleRecetaFormSet(instance=None)

    context = {
        'form': form,
        'formset': formset,
        'is_create': True
    }
    return render(request, "recetas/form_with_details.html", context)

@login_required
def receta_update(request, pk):
    """Actualizar receta existente con sus detalles (solo personal autorizado)"""
    if request.user.rol not in ['farmaceutico', 'administrador']:
        messages.error(request, "No tiene permisos para editar recetas")
        return redirect('recetas:list')

    receta = get_object_or_404(Receta, pk=pk)

    if request.method == "POST":
        form = RecetaForm(request.POST, instance=receta)
        formset = DetalleRecetaFormSet(request.POST, instance=receta)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, "Receta actualizada exitosamente")
            return redirect('recetas:detalle', pk=receta.pk)
    else:
        form = RecetaForm(instance=receta)
        formset = DetalleRecetaFormSet(instance=receta)

    context = {
        'form': form,
        'formset': formset,
        'receta': receta,
        'is_create': False
    }
    return render(request, "recetas/form_with_details.html", context)

@login_required
def receta_delete(request, pk):
    """Eliminar receta (solo personal autorizado)"""
    if request.user.rol not in ['farmaceutico', 'administrador']:
        messages.error(request, "No tiene permisos para eliminar recetas")
        return redirect('recetas:list')

    receta = get_object_or_404(Receta, pk=pk)
    
    if request.method == "POST":
        receta.delete()
        messages.success(request, "Receta eliminada exitosamente")
        return redirect('recetas:list')
    
    return render(request, "recetas/delete.html", {"receta": receta})

@login_required
def agregar_detalle(request, receta_id):
    """Agregar detalle a una receta existente"""
    if request.user.rol not in ['farmaceutico', 'administrador']:
        messages.error(request, "No tiene permisos para modificar recetas")
        return redirect('recetas:list')

    receta = get_object_or_404(Receta, pk=receta_id)
    
    if request.method == "POST":
        form = DetalleRecetaForm(request.POST)
        if form.is_valid():
            detalle = form.save(commit=False)
            detalle.receta = receta
            detalle.save()
            messages.success(request, "Medicamento agregado a la receta")
            return redirect('recetas:detalle', pk=receta.pk)
    else:
        form = DetalleRecetaForm()

    return render(request, "recetas/detalle_form.html", {
        "form": form,
        "receta": receta
    })

@login_required
def detalle_update(request, pk):
    """Actualizar un detalle de receta existente"""
    if request.user.rol not in ['farmaceutico', 'administrador']:
        messages.error(request, "No tiene permisos para modificar detalles de recetas")
        return redirect('recetas:list')

    detalle = get_object_or_404(DetalleReceta, pk=pk)
    receta = detalle.receta
    
    if request.method == "POST":
        form = DetalleRecetaForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            messages.success(request, "Detalle de receta actualizado exitosamente")
            return redirect('recetas:detalle', pk=receta.pk)
    else:
        form = DetalleRecetaForm(instance=detalle)

    return render(request, "recetas/detalle_form.html", {
        "form": form,
        "receta": receta,
        "detalle": detalle,
        "is_update": True
    })

@login_required
def detalle_delete(request, pk):
    """Eliminar un detalle de receta"""
    if request.user.rol not in ['farmaceutico', 'administrador']:
        messages.error(request, "No tiene permisos para eliminar detalles de recetas")
        return redirect('recetas:list')

    detalle = get_object_or_404(DetalleReceta, pk=pk)
    receta = detalle.receta
    
    if request.method == "POST":
        detalle.delete()
        messages.success(request, "Medicamento eliminado de la receta")
        return redirect('recetas:detalle', pk=receta.pk)
    
    return render(request, "recetas/detalle_delete.html", {
        "detalle": detalle,
        "receta": receta
    })
