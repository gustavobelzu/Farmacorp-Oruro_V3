from django.db import models
from farmacia.models import Sucursal

class Reporte(models.Model):
    id_Reporte=models.AutoField(primary_key=True)
    Fecha_Reporte=models.DateField(auto_now_add=True)
    Tipo=models.CharField(max_length=20)
    Sucursal=models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name="reportes")
