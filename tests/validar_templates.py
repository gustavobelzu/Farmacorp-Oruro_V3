#!/usr/bin/env python
"""
Validación completa de templates - Verificar errores y flujo de datos
"""
import os
import sys
import django
import re
from pathlib import Path

sys.path.insert(0, r'.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.template import Template, Context
from django.template.loader import get_template
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 90)
print("VALIDACIÓN COMPLETA DE TEMPLATES - FARMACORP-ORURO")
print("=" * 90)

# Encontrar todos los templates
templates_dir = Path('templates')
html_files = list(templates_dir.rglob('*.html'))

print(f"\n📁 Total de templates encontrados: {len(html_files)}")
print("-" * 90)

# Variables para tracking
errors = []
warnings = []
template_analysis = []

# ============================================================================
# PARTE 1: Análisis Estático de Templates
# ============================================================================
print("\n[1] ANÁLISIS ESTÁTICO DE TEMPLATES")
print("-" * 90)

for template_file in sorted(html_files):
    rel_path = template_file.relative_to(templates_dir)
    
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Revisar variables indefinidas
        variable_pattern = r'\{\{\s*(\w+(?:\.\w+)*)\s*\}\}'
        variables = set(re.findall(variable_pattern, content))
        
        # Revisar tags de template
        tag_pattern = r'\{%\s*(\w+)'
        tags = set(re.findall(tag_pattern, content))
        
        # Revisar for loops
        for_loops = re.findall(r'\{%\s*for\s+(\w+)\s+in\s+(\w+(?:\.\w+)*)', content)
        
        # Revisar if statements
        if_statements = re.findall(r'\{%\s*if\s+([^%]+)', content)
        
        # Revisar errores comunes
        if '{{' in content and '}}' not in content:
            issues.append("⚠️  Variables sin cerrar {{ }}")
        
        if '{%' in content and '%}' not in content:
            issues.append("⚠️  Tags sin cerrar {% %}")
        
        if 'undefined' in content.lower():
            issues.append("⚠️  Referencia a 'undefined' encontrada")
        
        # Revisar load de filters
        load_statements = re.findall(r'\{%\s*load\s+([^%]+)', content)
        
        template_analysis.append({
            'file': str(rel_path),
            'variables': variables,
            'tags': tags,
            'for_loops': for_loops,
            'if_statements': len(if_statements),
            'load_statements': load_statements,
            'issues': issues,
            'size': len(content)
        })
        
        if issues:
            print(f"❌ {rel_path}")
            for issue in issues:
                print(f"   {issue}")
                errors.append(f"{rel_path}: {issue}")
        else:
            print(f"✅ {rel_path}")
    
    except Exception as e:
        print(f"❌ {rel_path} - Error al leer: {e}")
        errors.append(f"{rel_path}: Error al leer - {e}")

# ============================================================================
# PARTE 2: Pruebas de Acceso a Vistas
# ============================================================================
print("\n\n[2] PRUEBAS DE ACCESO A VISTAS Y FLUJO DE DATOS")
print("-" * 90)

test_urls = [
    ('/usuario/login/', 'GET', {}, 'Login'),
    ('/usuario/register/', 'GET', {}, 'Register'),
    ('/reportes/', 'GET', {}, 'Reportes List'),
    ('/reportes/ganancias-sin-perdidas/', 'GET', {}, 'Reporte Ganancias'),
    ('/reportes/producto-mas-caro/', 'GET', {}, 'Reporte Producto Caro'),
    ('/clientes/', 'GET', {}, 'Clientes List'),
    ('/productos/', 'GET', {}, 'Productos List'),
]

client = Client()

for url, method, data, name in test_urls:
    try:
        if method == 'GET':
            response = client.get(url)
        else:
            response = client.post(url, data)
        
        # Verificar status code
        if response.status_code in [200, 301, 302]:
            status_ok = "✅"
        else:
            status_ok = "❌"
            warnings.append(f"{name} ({url}): Status {response.status_code}")
        
        print(f"{status_ok} {name:30} - Status: {response.status_code}")
        
        # Revisar si hay errores en el template
        if hasattr(response, 'content'):
            content_str = response.content.decode('utf-8', errors='ignore')
            if 'error' in content_str.lower() and 'form-error' not in content_str:
                warnings.append(f"{name}: Contiene palabra 'error'")
    
    except Exception as e:
        print(f"❌ {name:30} - Error: {e}")
        errors.append(f"{name} ({url}): {e}")

# ============================================================================
# PARTE 3: Validación de Variables Críticas
# ============================================================================
print("\n\n[3] VALIDACIÓN DE VARIABLES CRÍTICAS EN TEMPLATES")
print("-" * 90)

critical_variables = {
    'login': ['form', 'next'],
    'register': ['form'],
    'reportes/list': ['reportes'],
    'reportes/reporte_ganancias': ['detalles_sin_perdidas', 'productos_top', 'total_ganancia'],
    'reportes/reporte_producto_mas_caro': ['detalles_ordenados', 'productos_caros'],
    'clientes/list': ['clientes'],
    'productos/list': ['productos'],
}

for template_name, required_vars in critical_variables.items():
    template_data = next((t for t in template_analysis if template_name.lower() in t['file'].lower()), None)
    
    if template_data:
        print(f"\n📄 {template_data['file']}")
        print(f"   Variables encontradas: {len(template_data['variables'])}")
        
        for required_var in required_vars:
            if any(required_var in var for var in template_data['variables']):
                print(f"   ✅ Variable '{required_var}' presente")
            else:
                print(f"   ⚠️  Variable '{required_var}' NO ENCONTRADA")
                warnings.append(f"{template_data['file']}: Variable '{required_var}' faltante")
    else:
        print(f"\n⚠️  Template '{template_name}' no encontrado")

# ============================================================================
# PARTE 4: Análisis de Herencia y Bloques
# ============================================================================
print("\n\n[4] ANÁLISIS DE HERENCIA DE TEMPLATES")
print("-" * 90)

base_templates = []
child_templates = []

for analysis in template_analysis:
    content = ""
    try:
        with open(templates_dir / analysis['file'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'extends' in content:
            parent = re.search(r'\{%\s*extends\s+["\']([^"\']+)["\']', content)
            if parent:
                child_templates.append({
                    'file': analysis['file'],
                    'parent': parent.group(1)
                })
        
        if 'block ' in content:
            blocks = re.findall(r'\{%\s*block\s+(\w+)', content)
            if blocks:
                base_templates.append({
                    'file': analysis['file'],
                    'blocks': blocks
                })
    except:
        pass

print(f"\n✅ Base templates (con bloques): {len(base_templates)}")
for base in base_templates[:5]:
    print(f"   • {base['file']} - Bloques: {', '.join(base['blocks'][:3])}")

print(f"\n✅ Child templates (que heredan): {len(child_templates)}")
for child in child_templates[:5]:
    print(f"   • {child['file']} extends {child['parent']}")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n\n" + "=" * 90)
print("📊 RESUMEN DE VALIDACIÓN")
print("=" * 90)

print(f"\n✅ Templates válidos: {len(html_files) - len(errors)}/{len(html_files)}")
print(f"❌ Errores encontrados: {len(errors)}")
print(f"⚠️  Advertencias: {len(warnings)}")

if errors:
    print("\n❌ ERRORES CRÍTICOS:")
    for error in errors[:10]:
        print(f"   • {error}")

if warnings:
    print("\n⚠️  ADVERTENCIAS:")
    for warning in warnings[:10]:
        print(f"   • {warning}")

print("\n✨ ESTADO GENERAL: ", end="")
if len(errors) == 0:
    print("✅ TODOS LOS TEMPLATES SON VÁLIDOS")
else:
    print(f"⚠️  {len(errors)} ERRORES A REVISAR")

print("\n" + "=" * 90)
