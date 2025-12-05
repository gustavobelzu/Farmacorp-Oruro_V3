from django.test.client import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from reportes import views as rviews
from reportes.models import Reporte
from farmacia.models import Sucursal

# Crear request factory y usuario admin de prueba
factory = RequestFactory()
User = get_user_model()
user, created = User.objects.get_or_create(username='__export_test_admin__')
if created:
    user.set_password('testpass')
    user.is_staff = True
    user.is_active = True
    user.save()

# Tomar una sucursal existente o crear una mínima
s = Sucursal.objects.first()
if not s:
    f = None
    try:
        from farmacia.models import Farmacia
        f = Farmacia.objects.first() or Farmacia.objects.create(nombre_farmacia='Prueba')
    except Exception:
        f = None
    s = Sucursal.objects.create(nombre='Central', departamento='Oruro', nit='1234567890', email='suc@local', direccion='Calle 1', farmacia=f)

# Llamar exportar_excel
req = factory.get('/reportes/exportar/excel/', {'fecha_inicio': timezone.now().date().isoformat(), 'fecha_fin': timezone.now().date().isoformat(), 'sucursal': s.id_sucursal})
req.user = user
resp = rviews.exportar_excel(req)
print('exportar_excel status:', getattr(resp, 'status_code', 'n/a'))

# Llamar exportar_pdf
req2 = factory.get('/reportes/exportar/pdf/', {'fecha_inicio': timezone.now().date().isoformat(), 'fecha_fin': timezone.now().date().isoformat(), 'sucursal': s.id_sucursal})
req2.user = user
resp2 = rviews.exportar_pdf(req2)
print('exportar_pdf status:', getattr(resp2, 'status_code', 'n/a'))

# Llamar exportar_ganancias_sin_perdidas_excel
req3 = factory.get('/reportes/exportar/ganancias_sin_perdidas/', {'fecha_inicio': timezone.now().date().isoformat(), 'fecha_fin': timezone.now().date().isoformat(), 'sucursal': s.id_sucursal})
req3.user = user
try:
    resp3 = rviews.exportar_ganancias_sin_perdidas_excel(req3)
    print('exportar_ganancias_sin_perdidas_excel status:', getattr(resp3, 'status_code', 'n/a'))
except Exception as e:
    print('exportar_ganancias_sin_perdidas_excel exception:', e)

# Listar últimos reportes
print('Últimos Reportes:')
for r in Reporte.objects.order_by('-Fecha_Reporte')[:10]:
    print(r.id_Reporte, r.Fecha_Reporte, r.Tipo, getattr(r.Sucursal, 'id_sucursal', None))
