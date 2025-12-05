from django.contrib.auth.models import AbstractUser
from django.db import models
from empleados.models import Empleado
from clientes.models import Cliente
from django.utils import timezone
from datetime import timedelta

class Usuario(AbstractUser):
    ci_empleado = models.OneToOneField(Empleado, on_delete=models.CASCADE, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ci_cliente=models.OneToOneField(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    # defaults recomendados
    is_active = models.BooleanField(default=True)       # usuario habilitado al crearse
    is_staff = models.BooleanField(default=False)       # no acceso admin por defecto
    is_superuser = models.BooleanField(default=False)   # sin permisos totales por defecto
    date_joined = models.DateTimeField(auto_now_add=True)  # se llena automáticamente
    @property
    def rol(self):
        """
        Retorna el rol del usuario basado en sus relaciones.
        Devuelve: 'cliente', 'farmaceutico', 'encargado_almacen', 'administrador', o 'sin_rol'
        """
        if self.is_superuser or self.is_staff:
            return 'administrador'
        elif self.ci_empleado:
            # Mapear los cargos del empleado (en empleados.models.Empleado.CARGOS)
            cargo = self.ci_empleado.cargo
            cargo_map = {
                'farmaceutico': 'farmaceutico',
                'inventario': 'encargado_almacen',  # Mapear 'inventario' (cargo en BD) → 'encargado_almacen' (rol)
                'administrador': 'administrador',
            }
            return cargo_map.get(cargo, 'farmaceutico')
        elif self.ci_cliente:
            return 'cliente'
        return 'sin_rol'

    def save(self, *args, **kwargs):
        # Si está vinculado a un empleado
        if self.ci_empleado:
            self.first_name = self.ci_empleado.nombre
            self.last_name = self.ci_empleado.apellido
        # Si está vinculado a un cliente
        elif self.ci_cliente:
            self.first_name = self.ci_cliente.nombre
            self.last_name = self.ci_cliente.apellido

        super().save(*args, **kwargs)
    @property
    def nombre_completo(self):
        return f"{self.first_name} {self.last_name}"

    # -- Campos y métodos para bloqueo por intentos fallidos --
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    lockout_until = models.DateTimeField(null=True, blank=True)

    def register_failed_login(self):
        """Incrementa el contador de intentos fallidos y, si corresponde, calcula un período de bloqueo."""
        now = timezone.now()
        # Si el último fallo fue hace mucho tiempo, reiniciamos el contador (p.ej. > 1 hora)
        if self.last_failed_login and (now - self.last_failed_login) > timedelta(hours=1):
            self.failed_login_attempts = 0

        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        self.last_failed_login = now

        # Cada 3 intentos fallidos se aplica un bloqueo incremental
        if self.failed_login_attempts % 3 == 0:
            cycles = self.failed_login_attempts // 3
            # bloqueo en minutos: 1, 2, 4, 8, ... (doble por ciclo)
            lock_minutes = 1 * (2 ** (max(0, cycles - 1)))
            self.lockout_until = now + timedelta(minutes=lock_minutes)

        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'lockout_until'])

    def reset_failed_logins(self):
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.lockout_until = None
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'lockout_until'])

