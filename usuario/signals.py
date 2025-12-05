from django.apps import AppConfig
from django.contrib.auth.models import Group, Permission

class UsuariosConfig(AppConfig):
    name = 'usuarios'
    def ready(self):
        from django.contrib.auth.models import Group
        Group.objects.get_or_create(name='Administrador')
        Group.objects.get_or_create(name='farmaceutico')
        Group.objects.get_or_create(name='jefe_almacen')
        Group.objects.get_or_create(name='cliente')
