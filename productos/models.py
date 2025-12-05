from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator, MaxValueValidator
from decimal import Decimal
import json
from datetime import date

class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(
        max_length=40,
        validators=[RegexValidator(
            regex=r'^[A-Za-zÁÉÍÓÚáéíóúñÑ\s]+$',
            message='El nombre solo debe contener letras y espacios'
        )]
    )
    telefono = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message='El número de teléfono debe estar en formato: +999999999'
        )]
    )
    email = models.EmailField(unique=True,max_length=30)
    direccion = models.TextField(max_length=30)
    estado = models.BooleanField(default=True)
    fecha_registro = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.nombre} ({self.email})"

    def clean(self):
        # Convertir el nombre a título para consistencia
        self.nombre = self.nombre.title()


class Producto(models.Model):
    codigo_barras = models.CharField(
        max_length=20,
        primary_key=True,
        validators=[RegexValidator(
            regex=r'^[0-9]{8,13}$',
            message='El código de barras debe tener entre 8 y 13 dígitos'
        )]
    )
    nombre = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^[A-Za-z0-9ÁÉÍÓÚáéíóúñÑ\s\-\_\.]+$',
            message='El nombre solo puede contener letras, números, espacios y guiones'
        )]
    )
    descripcion = models.TextField()
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('1000000.00'))]
    )
    estado = models.BooleanField(default=True)
    stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0),MaxValueValidator(1000)]
    )
    fecha_vencimiento = models.DateField()
    iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,  # Proteger contra eliminación accidental
        related_name="productos"
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['codigo_barras']),
        ]

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock})"

    def clean(self):
        if self.fecha_vencimiento and self.fecha_vencimiento < date.today():
            raise ValidationError('La fecha de vencimiento no puede ser anterior a hoy')
        
        if self.precio_unitario is not None and self.precio_unitario <= 0:
            raise ValidationError('El precio debe ser mayor a 0')
        
        if self.stock is not None and self.stock < 0:
            raise ValidationError('El stock no puede ser negativo')
            
        if self.iva is not None and (self.iva < 0 or self.iva > 100):
            raise ValidationError('El IVA debe estar entre 0 y 100')

    def esta_por_vencer(self, dias=30):
        """Verifica si el producto está próximo a vencer"""
        if self.fecha_vencimiento:
            dias_restantes = (self.fecha_vencimiento - date.today()).days
            return dias_restantes <= dias
        return False

    def stock_bajo(self, minimo=10):
        """Verifica si el producto tiene stock bajo"""
        return self.stock <= minimo

    
    
class Compra(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="compras"
    )
    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('10000000.00'))]
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1),MaxValueValidator(10000)]
    )
    fecha_compra = models.DateTimeField(auto_now_add=True)
    nro_factura = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex=r'^[A-Z0-9\-]+$',
            message='El número de factura solo puede contener letras, números y guiones'
        )]
    )
    
    def clean(self):
            if self.precio_compra is None:
                raise ValidationError('El precio de compra no puede estar vacío')
            if self.cantidad is None:
                raise ValidationError('La cantidad no puede estar vacía')
            if self.precio_compra <= 0:
                raise ValidationError('El precio debe ser mayor a 0')
            if self.cantidad <= 0:
                raise ValidationError('La cantidad debe ser mayor a 0')
            if (self.cantidad != 0) and (self.precio_compra / self.cantidad <= 0):
                raise ValidationError('El precio unitario calculado debe ser mayor a 0')

    def save(self, *args, **kwargs):
        self.clean()
        # Calcular nuevo stock y precio promedio
        stock_actual = self.producto.stock
        precio_actual = self.producto.precio_unitario
        
        # Calcular nuevo precio promedio ponderado
        nuevo_stock = stock_actual + self.cantidad
        if nuevo_stock > 0:
            precio_promedio = ((stock_actual * precio_actual) + (self.cantidad * (self.precio_compra / self.cantidad))) / nuevo_stock
            self.producto.precio_unitario = round(precio_promedio, 2)
        
        # Actualizar stock
        self.producto.stock = nuevo_stock
        self.producto.save()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Compra de {self.producto.nombre} - {self.cantidad} unidades - {self.fecha_compra}"

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ["-fecha_compra"]
        indexes = [
            models.Index(fields=['fecha_compra']),
            models.Index(fields=['producto']),
        ]
