from django.db import models
from productos.models import Producto

class Alerta(models.Model):
    id_alerta = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()
    fecha_alerta = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="alertas")

    def __str__(self):
        return f"Alerta {self.tipo} - {self.producto.nombre}"
