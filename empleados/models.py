from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MinLengthValidator
from decimal import Decimal
from farmacia.models import Sucursal

class Empleado(models.Model):
    CARGOS = [
        ("farmaceutico", "Farmacéutico"),
        ("administrador", "Administrador"),
        ("inventario", "Encargado de Inventario"),
    ]
    
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro')
    ]
    
    TURNO_CHOICES = [
        ('mañana', 'Mañana (06:00 - 14:00)'),
        ('tarde', 'Tarde (14:00 - 22:00)'),
        ('noche', 'Noche (22:00 - 06:00)'),
    ]

    ci = models.CharField(
        max_length=20,
        primary_key=True,
        validators=[
            RegexValidator(
                regex=r'^[0-9]{6,10}[A-Z]?$',
                message='CI debe tener entre 6-10 dígitos y opcionalmente una letra mayúscula'
            )
        ]
    )
    nombre = models.CharField(
        max_length=25,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-zÁÉÍÓÚáéíóúñÑ\s]+$',
                message='El nombre solo debe contener letras y espacios'
            ),
            MinLengthValidator(3, 'El nombre debe tener al menos 3 caracteres')
        ]
    )
    apellido = models.CharField(
        max_length=25,default="Sin apellido",
        validators=[
            RegexValidator(
                regex=r'^[A-Za-zÁÉÍÓÚáéíóúñÑ\s]+$',
                message='El apellido solo debe contener letras y espacios'
            ),
            MinLengthValidator(3, 'El apellido debe tener al menos 3 caracteres')
        ]
    )
    direccion = models.CharField(
        max_length=30,
        validators=[MinLengthValidator(5, 'La dirección debe tener al menos 5 caracteres')]
    )
    telefono = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{8,15}$',
                message='El número de teléfono debe tener entre 8 y 15 dígitos'
            )
        ]
    )
    salario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    cargo = models.CharField(
        max_length=20,
        choices=CARGOS
    )
    sexo = models.CharField(
        max_length=1,
        choices=SEXO_CHOICES
    )
    estado = models.BooleanField(default=True)
    turno = models.CharField(
        max_length=20,
        choices=TURNO_CHOICES
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.PROTECT,
        related_name='empleados'
    )
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    def __str__(self):
        return f"{self.nombre} - {self.cargo}"
    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['ci']),
            models.Index(fields=['cargo']),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.get_cargo_display()} ({self.sucursal.nombre})"

    def clean(self):
        # Convertir nombre a título para consistencia
        self.nombre = self.nombre.title()
        self.direccion = ' '.join(self.direccion.split())
        
        # Validaciones específicas
        if self.salario < 0:
            raise ValidationError('El salario no puede ser negativo')
            
        if len(self.nombre.strip()) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres')
            
        if len(self.direccion.strip()) < 5:
            raise ValidationError('La dirección debe tener al menos 5 caracteres')

    def save(self, *args, **kwargs):
        self.clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Crear/actualizar perfil específico basado en el cargo
        # Siempre ejecutar: si es nuevo o si el cargo cambió
        if self.cargo == "farmaceutico":
            Farmaceutico.objects.get_or_create(empleado=self)
            # Limpiar perfiles de otros cargos si existen
            Administrador.objects.filter(empleado=self).delete()
            EncargadoInventario.objects.filter(empleado=self).delete()
        elif self.cargo == "administrador":
            Administrador.objects.get_or_create(empleado=self)
            # Limpiar perfiles de otros cargos si existen
            Farmaceutico.objects.filter(empleado=self).delete()
            EncargadoInventario.objects.filter(empleado=self).delete()
        elif self.cargo == "inventario":
            EncargadoInventario.objects.get_or_create(empleado=self)
            # Limpiar perfiles de otros cargos si existen
            Farmaceutico.objects.filter(empleado=self).delete()
            Administrador.objects.filter(empleado=self).delete()

    def get_ventas_mes(self):
        """Retorna el total de ventas del mes actual"""
        from django.utils import timezone
        from datetime import timedelta
        
        inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        return self.ventas.filter(
            fecha__gte=inicio_mes
        ).aggregate(total=models.Sum('total'))['total'] or 0


class Farmaceutico(models.Model):
    empleado = models.OneToOneField(
        Empleado,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='perfil_farmaceutico'
    )
    matricula = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9\-]+$',
                message='La matrícula solo puede contener letras, números y guiones'
            )
        ],
        unique=True
    )
    especialidad = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-zÁÉÍÓÚáéíóúñÑ\s]+$',
                message='La especialidad solo debe contener letras y espacios'
            )
        ]
    )

    def __str__(self):
        return f"Farm. {self.empleado.nombre} - Mat: {self.matricula}"


class Administrador(models.Model):
    empleado = models.OneToOneField(
        Empleado,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='perfil_administrador'
    )

    def __str__(self):
        return f"Admin. {self.empleado.nombre}"


class EncargadoInventario(models.Model):
    empleado = models.OneToOneField(
        Empleado,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='perfil_inventario'
    )

    def __str__(self):
        return f"Inv. {self.empleado.nombre}"
