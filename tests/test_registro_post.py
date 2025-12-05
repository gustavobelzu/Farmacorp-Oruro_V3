#!/usr/bin/env python
"""
Prueba de POST a la vista de registro con datos de cliente.
Simula lo que hace el navegador al enviar el formulario.
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

# Limpiar clientes y usuarios previos de prueba
Cliente.objects.filter(ci_cliente='8888888').delete()
Usuario.objects.filter(username__startswith='cli_8888').delete()

# Crear cliente de prueba
cliente = Cliente.objects.create(
    ci_cliente='8888888',
    nombre='TestCliente',
    apellido='Registro',
    telefono='76123456',
    direccion='Calle Test 456'
)
print(f'✓ Cliente creado: {cliente}')

# Simular POST al formulario de registro
client = Client()
data = {
    'email': 'testcliente@example.com',
    'password1': 'SecurePass123!',
    'password2': 'SecurePass123!',
    'ci_cliente': cliente.ci_cliente,  # Usar el ci_cliente como valor
}

print('\n=== POST DATA ===')
for k, v in data.items():
    print(f'{k}: {v}')

response = client.post('/usuario/register/', data)

print(f'\n=== RESPONSE STATUS: {response.status_code} ===')
print(f'Content-Type: {response.get("Content-Type")}')

if response.status_code == 302:
    print(f'✓ Redirect to: {response.url}')
    print('✓ Usuario probablemente creado exitosamente')
    # Verificar si existe el usuario
    usuarios = Usuario.objects.filter(ci_cliente=cliente)
    print(f'\nUsuarios asociados al cliente: {list(usuarios.values_list("username", flat=True))}')
else:
    print(f'\n=== RESPONSE CONTENT (primeros 2000 chars) ===')
    print(response.content.decode('utf-8')[:2000])
    
    # Si hay formulario con errores, extraer errores
    if hasattr(response, 'context') and response.context:
        form = response.context.get('form')
        if form:
            print(f'\n=== FORM ERRORS ===')
            print(form.errors.as_json() if form.errors else 'Sin errores en el contexto')
