from django.db import models
from django.core.validators import MinValueValidator,MaxValueValidator
from django.core.exceptions import ValidationError
from farmacia.models import Sucursal
from productos.models import Producto
from utils.stock import actualizar_stock_producto

class Inventario(models.Model):
    id_inventario = models.AutoField(primary_key=True)
    cantidad = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(1000)])
    estado = models.BooleanField(default=True)
    fecha_actualizacion = models.DateField(auto_now=True)
    stock_minimo = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    ubicacion=models.CharField(max_length=20,default="Almacen Central")
    

    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} ({self.sucursal.nombre})"

    def clean(self):
        # Validaciones básicas
        errors = {}
        if self.cantidad is None:
            errors['cantidad'] = 'La cantidad es requerida.'
        elif self.cantidad < 0:
            errors['cantidad'] = 'La cantidad no puede ser negativa.'

        if self.stock_minimo is None:
            errors['stock_minimo'] = 'El stock mínimo es requerido.'
        elif self.stock_minimo < 0:
            errors['stock_minimo'] = 'El stock mínimo no puede ser negativo.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Ejecutar validaciones de modelo antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)
        # Actualizar stock en sistema (no lanzar error al usuario si falla)
        try:
            actualizar_stock_producto(self.producto)
        except Exception:
            pass

    @property
    def estado_stock(self):
        """Retorna el estado del stock basado en la cantidad y el stock mínimo"""
        if self.cantidad == 0:
            return "Sin Stock"
        elif self.cantidad <= self.stock_minimo:
            return "Stock Bajo"
        return "En Stock"
    
    @property
    def estado_stock_class(self):
        """Retorna la clase CSS para el estado del stock"""
        estados = {
            "Sin Stock": "bg-danger",
            "Stock Bajo": "bg-warning text-dark",
            "En Stock": "bg-success"
        }
        return estados.get(self.estado_stock)
    
    @property
    def estado_stock_icon(self):
        """Retorna el icono para el estado del stock"""
        estados = {
            "Sin Stock": "fas fa-times-circle",
            "Stock Bajo": "fas fa-exclamation-triangle",
            "En Stock": "fas fa-check-circle"
        }
        return estados.get(self.estado_stock)
    
    class Meta:
        verbose_name = "Inventario"
        verbose_name_plural = "Inventarios"
        ordering = ['-fecha_actualizacion']

