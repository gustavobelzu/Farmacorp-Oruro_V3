from django.db import models
from clientes.models import Cliente
from empleados.models import Empleado
from productos.models import Producto

class Receta(models.Model):
    id_receta = models.AutoField(primary_key=True)
    fecha_emision = models.DateField()
    Matricula_medico=models.CharField(max_length=20)
    Medicamento=models.CharField(max_length=30)
    Cantidad=models.IntegerField()
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="recetas")
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="recetas")

    def __str__(self):
        return f"Receta {self.id_receta} - {self.cliente.nombre}"


class DetalleReceta(models.Model):
    id_detalleReceta = models.AutoField(primary_key=True)
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="detalles_recetas")
    dosis = models.CharField(max_length=50)
    frecuencia = models.CharField(max_length=20)
    duracion = models.CharField(max_length=20)
    instrucciones = models.TextField()

    def __str__(self):
        return f"{self.receta.id_receta} - {self.producto.nombre}"
