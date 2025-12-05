from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Empleado
from .forms import EmpleadoForm

def empleado_list(request):
     if request.user.rol == 'administrador' :
        empleados = Empleado.objects.all()
        return render(request, "empleados/list.html", {"empleados": empleados})
     else:
        messages.error(request, "No tiene permisos para ver empleados")
        return redirect('usuario:dashboard')

def empleado_create(request):
    form = EmpleadoForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("empleados:list")
    return render(request, "empleados/form.html", {"form": form})

def empleado_update(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    form = EmpleadoForm(request.POST or None, instance=empleado)
    if form.is_valid():
        form.save()
        return redirect("empleados:list")
    return render(request, "empleados/form.html", {"form": form})

def empleado_delete(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)
    if request.method == "POST":
        empleado.delete()
        return redirect("empleados:list")
    return render(request, "empleados/delete.html", {"empleado": empleado})
