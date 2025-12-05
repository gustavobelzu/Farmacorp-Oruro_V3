from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinLengthValidator

class Farmacia(models.Model):
    id_farmacia = models.AutoField(primary_key=True)
    nombre_farmacia = models.CharField(
        max_length=30,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9ÁÉÍÓÚáéíóúñÑ\s\-\.]+$',
                message='El nombre solo puede contener letras, números, espacios, guiones y puntos'
            ),
            MinLengthValidator(3, 'El nombre debe tener al menos 3 caracteres')
        ]
    )
    razon_legal = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9ÁÉÍÓÚáéíóúñÑ\s\-\.]+$',
                message='La razón legal solo puede contener letras, números, espacios, guiones y puntos'
            )
        ]
    )
    
    class Meta:
        verbose_name = "Farmacia"
        verbose_name_plural = "Farmacias"
        ordering = ['nombre_farmacia']
        indexes = [
            models.Index(fields=['nombre_farmacia']),
        ]

    def __str__(self):
        return self.nombre_farmacia


    def clean(self):
        self.nombre_farmacia = self.nombre_farmacia.title()
        if self.razon_legal:
            self.razon_legal = self.razon_legal.upper()

        if len(self.nombre_farmacia.strip()) < 3:
            raise ValidationError('El nombre de la farmacia debe tener al menos 3 caracteres')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def total_sucursales(self):
        """Retorna el número total de sucursales"""
        return self.sucursales.count()

    def sucursales_activas(self):
        """Retorna las sucursales activas"""
        return self.sucursales.filter(activa=True)


class Sucursal(models.Model):
    DEPARTAMENTOS = [
        ("Oruro", "Oruro"),
        ("La Paz", "La Paz"),
        ("Cochabamba", "Cochabamba"),
        ("Potosi", "Potosi"),
        ("Chuquisaca", "Chuquisaca"),
        ("Pando", "Pando"),
        ("Beni", "Beni"),
        ("Santa Cruz", "Santa Cruz"),
        ("Tarija", "Tarija"),
    ]

    HORARIOS = [
        ('completo', '24 horas'),
        ('diurno', '08:00 - 20:00'),
        ('extendido', '08:00 - 22:00'),
    ]

    id_sucursal = models.AutoField(primary_key=True)
    nombre = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z0-9ÁÉÍÓÚáéíóúñÑ\s\-\.]+$',
                message='El nombre solo puede contener letras, números, espacios, guiones y puntos'
            ),
            MinLengthValidator(3, 'El nombre debe tener al menos 3 caracteres')
        ]
    )
    departamento = models.CharField(
        max_length=30,
        choices=DEPARTAMENTOS
    )
    nit = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[0-9]{10,13}$',
                message='El NIT debe tener entre 10 y 13 dígitos'
            )
        ]
    )
    email = models.EmailField(unique=True)
    direccion = models.CharField(
        max_length=30,
        validators=[MinLengthValidator(5, 'La dirección debe tener al menos 5 caracteres')]
    )
    horario = models.CharField(
        max_length=20,
        choices=HORARIOS,
        default='diurno'
    )
   
    fecha_registroSucursal = models.DateTimeField(auto_now_add=True)
    farmacia = models.ForeignKey(
        Farmacia,
        on_delete=models.PROTECT,
        related_name="sucursales"
    )

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['departamento', 'nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['departamento']),
            models.Index(fields=['nit']),
        ]
        unique_together = [['farmacia', 'nombre']]

    def __str__(self):
        return f"{self.nombre} - {self.departamento}"


    def clean(self):
        self.nombre = self.nombre.title()
        self.direccion = ' '.join(self.direccion.split())
        
        if len(self.nombre.strip()) < 3:
            raise ValidationError('El nombre de la sucursal debe tener al menos 3 caracteres')
            
        if len(self.direccion.strip()) < 5:
            raise ValidationError('La dirección debe tener al menos 5 caracteres')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def total_empleados(self):
        """Retorna el número total de empleados en la sucursal"""
        return self.empleados.count()

    def total_ventas_mes(self):
        """Retorna el total de ventas del mes actual"""
        from django.utils import timezone
        from datetime import timedelta
        
        inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        return self.ventas.filter(
            fecha__gte=inicio_mes
        ).aggregate(total=models.Sum('total'))['total'] or 0
