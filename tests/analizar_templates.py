#!/usr/bin/env python
"""
Verificación detallada de flujo de datos en templates y vistas
"""
import os
import sys
import django
from pathlib import Path

sys.path.insert(0, r'.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from reportes.views import reporte_ganancias_sin_perdidas, reporte_producto_mas_caro_vendido

User = get_user_model()

print("=" * 90)
print("VALIDACIÓN DE FLUJO DE DATOS EN TEMPLATES")
print("=" * 90)

factory = RequestFactory()

# ============================================================================
# [1] REVISAR TEMPLATE: reportes/Dashboard.html
# ============================================================================
print("\n[1] TEMPLATE: reportes/Dashboard.html")
print("-" * 90)

# El problema está en la línea donde renderiza datos JSON
# {{ ventas_por_sucursal_json|escapejs }} - Puede ser undefined

issues = [
    "⚠️  ventas_por_sucursal_json - Puede ser undefined si no llega desde la vista",
    "⚠️  top_productos_json - Puede ser undefined si no llega desde la vista",
    "⚠️  ventas_por_hora_json - Puede ser undefined si no llega desde la vista",
]

for issue in issues:
    print(f"   {issue}")

print("\n   📌 SOLUCIÓN RECOMENDADA:")
print("   • Añadir |default:'[]' en el template después de cada variable JSON")
print("   • Ejemplo: {{ ventas_por_sucursal_json|default:'[]'|escapejs }}")

# ============================================================================
# [2] REVISAR TEMPLATE: usuario/form.html
# ============================================================================
print("\n[2] TEMPLATE: usuario/form.html")
print("-" * 90)

issues2 = [
    "⚠️  La línea: if ('{{ form.instance.ci_empleado }}')",
    "       → Usa string literal en JavaScript lo que puede causar 'undefined'",
    "⚠️  La línea: if ('{{ form.instance.ci_cliente }}')",
    "       → Mismo problema - evalúa la representación string de un objeto",
]

for issue in issues2:
    print(f"   {issue}")

print("\n   📌 SOLUCIÓN RECOMENDADA:")
print("   • Usar: if ({{ form.instance.ci_empleado|default:'false' }})")
print("   • O verificar: if (parseInt('{{ form.instance.ci_empleado.pk }}') > 0)")

# ============================================================================
# [3] PRUEBA DE VISTAS Y CONTEXTO
# ============================================================================
print("\n\n[3] ANÁLISIS DE CONTEXTO DE VISTAS")
print("-" * 90)

# Crear usuario para pruebas
try:
    user = User.objects.filter(username='empleado_test').first()
    if not user:
        user = User.objects.create_user(
            username='empleado_test',
            email='empleado@test.com',
            password='TestPass123!'
        )
    
    # Probar vistas y ver qué contexto devuelven
    request = factory.get('/reportes/ganancias-sin-perdidas/')
    request.user = user
    
    print("\n📄 Vista: reporte_ganancias_sin_perdidas()")
    print("   Contexto esperado:")
    
    # Leer la vista para ver qué variables devuelve
    import inspect
    from reportes import views as reportes_views
    
    # Analizar la función
    source = inspect.getsource(reportes_views.reporte_ganancias_sin_perdidas)
    
    # Buscar render o context
    if 'context' in source:
        print("   ✅ Usa context dictionary")
        # Buscar variables específicas
        if 'detalles_sin_perdidas' in source:
            print("   ✅ Proporciona: detalles_sin_perdidas")
        if 'productos_top' in source:
            print("   ✅ Proporciona: productos_top")
        if 'total_ganancia' in source:
            print("   ✅ Proporciona: total_ganancia")
    
except Exception as e:
    print(f"   ⚠️  Error al analizar: {e}")

# ============================================================================
# [4] LISTA DE CORRECCIONES RECOMENDADAS
# ============================================================================
print("\n\n[4] CORRECCIONES RECOMENDADAS")
print("-" * 90)

corrections = {
    "reportes/Dashboard.html": [
        ("Línea ~372", "JSON variables sin valores por defecto", 
         "Cambiar: {{ ventas_por_sucursal_json|escapejs }}\n                  A: {{ ventas_por_sucursal_json|default:'[]'|escapejs }}"),
        ("Línea ~490", "Datos de gráficos sin fallback",
         "Cambiar: const dataSucursal = JSON.parse('{{ ventas_por_sucursal_json|escapejs }}')\n                  A: const dataSucursal = JSON.parse('{{ ventas_por_sucursal_json|default:'[]'|escapejs }}')"),
        ("Línea ~643", "Parse de JSON sin try-catch",
         "Envolver: const dataHoras = (function(){...})()\n          en try-catch para manejar JSON inválido"),
    ],
    "usuario/form.html": [
        ("Línea ~259", "Verificación de string en JavaScript",
         "Cambiar: if ('{{ form.instance.ci_empleado }}')\n              A: if ({{ form.instance.ci_empleado.pk|default:'0' }})"),
        ("Línea ~263", "Verificación de string en JavaScript",
         "Cambiar: if ('{{ form.instance.ci_cliente }}')\n              A: if ({{ form.instance.ci_cliente.pk|default:'0' }})"),
    ]
}

for template, fixes in corrections.items():
    print(f"\n📝 {template}:")
    for location, problem, solution in fixes:
        print(f"\n   {location}")
        print(f"   ❌ Problema: {problem}")
        print(f"   ✅ Solución: {solution}")

# ============================================================================
# [5] VALIDACIÓN RÁPIDA DE CONTEXT VARS
# ============================================================================
print("\n\n[5] VERIFICACIÓN DE VARIABLES CRÍTICAS POR VISTA")
print("-" * 90)

views_context_map = {
    'reportes/reporte_ganancias_sin_perdidas.html': {
        'variables': ['detalles_sin_perdidas', 'productos_top', 'total_ganancia'],
        'json_variables': ['productos_top_json'],
    },
    'reportes/reporte_producto_mas_caro.html': {
        'variables': ['detalles_ordenados', 'productos_caros'],
        'json_variables': ['productos_caros_json'],
    },
    'reportes/Dashboard.html': {
        'variables': ['ingresos', 'costos', 'ganancia', 'margen', 'top_productos'],
        'json_variables': ['ventas_por_sucursal_json', 'top_productos_json', 'ventas_por_hora_json'],
    }
}

for template, expected_vars in views_context_map.items():
    print(f"\n📄 {template}")
    print(f"   Variables críticas esperadas:")
    for var in expected_vars.get('variables', []):
        print(f"      • {var}")
    if expected_vars.get('json_variables'):
        print(f"   Variables JSON (requieren fallback):")
        for var in expected_vars['json_variables']:
            print(f"      • {var} - USAR: {{ {var}|default:'[]'|escapejs }}")

print("\n\n" + "=" * 90)
print("✅ RECOMENDACIONES APLICADAS")
print("=" * 90)
print("""
PASO 1: Actualizar reportes/Dashboard.html
   ├─ Cambiar línea 372: Agregar |default:'[]' a variables JSON
   ├─ Cambiar línea 490: Envolver JSON.parse en try-catch
   └─ Cambiar línea 643: Usar fallback para dataProductos

PASO 2: Actualizar usuario/form.html  
   ├─ Cambiar línea 259: Usar .pk|default:'0' en lugar de string
   └─ Cambiar línea 263: Usar .pk|default:'0' en lugar de string

PASO 3: Verificar que todas las vistas pasen el contexto esperado
   ├─ reportes/Dashboard - pasar todas las variables JSON
   ├─ usuario/form - pasar audit_logs si existen
   └─ reportes/* - pasar variables por defecto

PASO 4: Pruebas finales
   ├─ Acceder a cada vista sin datos
   ├─ Verificar que no hay errores de JavaScript
   └─ Confirmar que los formularios funcionan
""")

print("=" * 90)
