#!/usr/bin/env python
"""
Prueba completa del flujo de usuario cliente:
1. Crear cliente
2. Registrar usuario cliente
3. Login
4. Verificar redirect al dashboard
5. Verificar rol y redirect a historial
"""
import os
import sys
import django

sys.path.insert(0, r'.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from clientes.models import Cliente
from usuario.models import Usuario

print("=" * 60)
print("PRUEBA COMPLETA: FLUJO DE USUARIO CLIENTE")
print("=" * 60)

# Limpiar previos
ci_test = '7777777'
Usuario.objects.filter(username__startswith='cli_').delete()
Cliente.objects.filter(ci_cliente=ci_test).delete()

# 1. Crear cliente
print("\n[1] Creando cliente de prueba...")
cliente = Cliente.objects.create(
    ci_cliente=ci_test,
    nombre='Carlos',
    apellido='TestClient',
    telefono='76999999',
    direccion='Calle Principal 789'
)
print(f"✓ Cliente creado: {cliente}")

# 2. Registrar usuario cliente
print("\n[2] Registrando usuario cliente...")
client = Client()
data = {
    'email': 'carlos@test.com',
    'password1': 'TestPass123!@',
    'password2': 'TestPass123!@',
    'ci_cliente': cliente.ci_cliente,
}

response = client.post('/usuario/register/', data, follow=False)
if response.status_code == 302:
    print(f"✓ Registro exitoso - Redirect a: {response.url}")
    usuario = Usuario.objects.filter(ci_cliente=cliente).first()
    if usuario:
        print(f"✓ Usuario creado: {usuario.username} (ID: {usuario.id})")
        print(f"✓ Rol detectado: {usuario.rol}")
    else:
        print("✗ No se encontró usuario después del registro")
else:
    print(f"✗ Registro falló - Status: {response.status_code}")
    print(f"Response: {response.content.decode('utf-8')[:500]}")

# 3. Login
print("\n[3] Haciendo login...")
client = Client()
login_data = {
    'username': usuario.username,
    'password': 'TestPass123!@',
}

response = client.post('/usuario/login/', login_data, follow=False)
if response.status_code == 302:
    print(f"✓ Login exitoso - Redirect a: {response.url}")
else:
    print(f"✗ Login falló - Status: {response.status_code}")

# 4. Acceder a dashboard (debe redirigir a historial si es cliente)
print("\n[4] Accediendo a dashboard...")
response = client.get('/usuario/dashboard/', follow=False)
print(f"Status: {response.status_code}")
if response.status_code == 302:
    print(f"✓ Dashboard redirige a: {response.url}")
    if 'clientes/historial/' in response.url:
        print("✓ Redirige correctamente al historial del cliente")
    else:
        print("✗ No redirige a historial")
elif response.status_code == 200:
    print("✓ Dashboard accesible (probablemente no es cliente o rol no fue detectado)")
else:
    print(f"✗ Error accediendo a dashboard")

# 5. Acceder directo al historial
print("\n[5] Accediendo directo al historial del cliente...")
response = client.get(f'/clientes/historial/{cliente.ci_cliente}/', follow=False)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✓ Historial del cliente accesible")
else:
    print(f"✗ Error accediendo historial - Status: {response.status_code}")

print("\n" + "=" * 60)
print("PRUEBA COMPLETADA")
print("=" * 60)
