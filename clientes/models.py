from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinLengthValidator

class Cliente(models.Model):
    ci_cliente = models.CharField(
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
    telefono = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{8,15}$',
                message='El número de teléfono debe tener entre 8 y 15 dígitos'
            )
        ]
    )
    direccion = models.CharField(
        max_length=30,
        validators=[MinLengthValidator(5, 'La dirección debe tener al menos 5 caracteres')]
    )
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['ci_cliente']),
        ]

    def __str__(self):
        return f"{self.nombre} (CI: {self.ci_cliente})"

    def clean(self):
        # Convertir nombre a título para consistencia
        self.nombre = self.nombre.title()
        
        # Limpiar espacios extra en los campos
        self.nombre = ' '.join(self.nombre.split())
        self.direccion = ' '.join(self.direccion.split())
        
        # Validar longitud mínima después de limpiar
        if len(self.nombre.strip()) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres')
        if len(self.direccion.strip()) < 5:
            raise ValidationError('La dirección debe tener al menos 5 caracteres')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_total_compras(self):
        """Retorna el total de compras del cliente"""
        return self.ventas.aggregate(
            total=models.Sum('total')
        )['total'] or 0

    def get_ultima_compra(self):
        """Retorna la fecha de la última compra"""
        return self.ventas.order_by('-fecha').first()
