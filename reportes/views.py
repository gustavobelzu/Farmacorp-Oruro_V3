from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, F, Count, Avg, Value, DecimalField, Max
from django.db.models.functions import Coalesce, ExtractHour
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models.expressions import ExpressionWrapper
from decimal import Decimal
import pandas as pd
import io
import json
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from ventas.models import Venta, DetalleVenta
from productos.models import Producto
from farmacia.models import Sucursal
from .models import Reporte
from .forms import ReporteForm
from django.conf import settings
from django.contrib import messages


def _crear_reporte_si_no_existe(tipo, sucursal_obj):
    """Crear un `Reporte` solo si no existe otro del mismo `tipo` y `Sucursal` para la misma fecha.

    Esto evita duplicados por doble-click o peticiones múltiples.
    """
    try:
        from django.utils import timezone
        hoy = timezone.now().date()
        existe = Reporte.objects.filter(Tipo=tipo, Sucursal=sucursal_obj, Fecha_Reporte=hoy).exists()
        if not existe:
            Reporte.objects.create(Tipo=tipo, Sucursal=sucursal_obj)
    except Exception:
        # No interrumpir la descarga si falla el logging
        pass

# --- Constantes ---
DEFAULT_DATE_RANGE = 30  # días
PRODUCTOS_TOP = 10
CACHE_TTL = 60 * 5  # 5 minutos

def decimal_sum(expr):
    """Helper para evitar error de tipos mezclados (Decimal vs Integer)"""
    return Sum(
        ExpressionWrapper(expr, output_field=DecimalField(max_digits=12, decimal_places=2)),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )

# DASHBOARD PRINCIPAL

def reporte_dashboard(request):
    """Dashboard general de reportes y estadísticas"""

    # --- Filtros ---
    fecha_fin = request.GET.get("fecha_fin", "").strip()
    fecha_inicio = request.GET.get("fecha_inicio", "").strip()
    sucursal_id = request.GET.get("sucursal", "").strip() or None

    # Usar valores por defecto si están vacíos
    if not fecha_inicio:
        fecha_inicio = timezone.now() - timedelta(days=DEFAULT_DATE_RANGE)
    if not fecha_fin:
        fecha_fin = timezone.now()

    # Convertir strings ISO a datetime
    if isinstance(fecha_inicio, str):
        try:
            fecha_inicio = datetime.fromisoformat(fecha_inicio)
        except (ValueError, TypeError):
            fecha_inicio = timezone.now() - timedelta(days=DEFAULT_DATE_RANGE)
    
    if isinstance(fecha_fin, str):
        try:
            fecha_fin = datetime.fromisoformat(fecha_fin)
        except (ValueError, TypeError):
            fecha_fin = timezone.now()

    # Si se recibieron fechas (date) en lugar de datetimes, normalizarlas al día completo
    if not isinstance(fecha_inicio, datetime):
        fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    if not isinstance(fecha_fin, datetime):
        fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    # Hacer aware si es naive (cuando USE_TZ=True en settings)
    try:
        if fecha_inicio.tzinfo is None:
            fecha_inicio = timezone.make_aware(fecha_inicio)
        if fecha_fin.tzinfo is None:
            fecha_fin = timezone.make_aware(fecha_fin)
    except Exception:
        pass

    # Normalizar a datetimes "aware" para evitar warnings cuando USE_TZ=True
    # Si el valor es una fecha (no datetime) lo convertimos al inicio/fin del día
    if not isinstance(fecha_inicio, datetime):
        fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    if not isinstance(fecha_fin, datetime):
        fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

    # Hacer aware si es naive
    try:
        if fecha_inicio.tzinfo is None:
            fecha_inicio = timezone.make_aware(fecha_inicio)
        if fecha_fin.tzinfo is None:
            fecha_fin = timezone.make_aware(fecha_fin)
    except Exception:
        # Si por alguna razón make_aware falla (entorno peculiar), continuar usando los datetimes
        pass

    # --- Intentar usar cache ---
    cache_key = f'dashboard_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}_{sucursal_id or "none"}'
    cached = cache.get(cache_key)
    if cached:
        return render(request, "reportes/dashboard.html", cached)

    # --- Query base ---
    # Incluir estados que representan ventas finalizadas en el sistema
    ventas = Venta.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin],
        estado__in=['completada', 'pagado']
    )
    if sucursal_id:
        ventas = ventas.filter(sucursal_id=sucursal_id)

    # --- Métricas principales ---
    metricas = ventas.aggregate(
        total_ventas=Coalesce(Sum('total'), Value(0), output_field=DecimalField()),
        num_ventas=Count('id_venta'),
        ticket_promedio=Coalesce(Avg('total'), Value(0), output_field=DecimalField())
    )

    # --- Productos más vendidos ---
    detalles = DetalleVenta.objects.filter(venta__in=ventas)
    top_productos = (
        detalles.values('producto__nombre', 'producto__codigo_barras', 'producto__stock')
        .annotate(
            cantidad_total=Coalesce(Sum('cantidad'), Value(0)),
            total_vendido=Coalesce(
                decimal_sum(F('cantidad') * F('precio_unitario')),
                Value(0),
                output_field=DecimalField()
            ),
            stock=F('producto__stock'),
            ganancia_total=Coalesce(Sum('ganancia'), Value(0), output_field=DecimalField())
        )
        .order_by('-cantidad_total')[:PRODUCTOS_TOP]
    )

    # Transformar para tener claves más intuitivas usadas por la plantilla/JS
    top_productos_list = []
    total_vendidos = 0
    for p in top_productos:
        tv = p.get('total_vendido') or 0
        total_vendidos += float(tv)
        top_productos_list.append({
            'nombre': p.get('producto__nombre'),
            'codigo': p.get('producto__codigo_barras'),
            'stock': p.get('producto__stock') or 0,
            'cantidad_total': int(p.get('cantidad_total') or 0),
            'total_vendido': float(p.get('total_vendido') or 0),
            'ganancia_total': float(p.get('ganancia_total') or 0)
        })

    # Calcular porcentaje del total vendido
    for p in top_productos_list:
        p['porcentaje_total'] = (p['total_vendido'] / total_vendidos * 100) if total_vendidos > 0 else 0

    # --- Análisis financiero general ---
    finanzas = detalles.aggregate(
        ingresos = Coalesce(
            decimal_sum(F('cantidad') * F('precio_unitario')),
            Value(0),
            output_field=DecimalField()
        ),
        ganancia=Coalesce(Sum('ganancia'), Value(0), output_field=DecimalField()),
        items_vendidos=Count('id'),
        productos_unicos=Count('producto', distinct=True)
    )
    margen = (finanzas['ganancia'] / finanzas['ingresos'] * 100) if finanzas['ingresos'] > 0 else 0

    # --- Ventas por hora ---
    ventas_por_hora = (
        ventas.annotate(hora=ExtractHour('fecha'))
        .values('hora')
        .annotate(
            total_ventas=Count('id_venta'),
            monto_total=Coalesce(Sum('total'), Value(0), output_field=DecimalField())
        )
        .order_by('hora')
    )

    # --- Ventas por sucursal (para gráfico) ---
    ventas_por_sucursal = (
        ventas.values('sucursal__nombre')
        .annotate(total=Coalesce(Sum('total'), Value(0), output_field=DecimalField()))
        .order_by('-total')
    )

    # --- Actividad reciente ---
    actividades_recientes = (
        ventas.select_related('sucursal', 'cliente')
        .order_by('-fecha')[:5]
        .values('fecha', 'total', 'cliente__nombre', 'sucursal__nombre')
    )

    # --- Preparar top_productos para plantilla y para JS ---
    top_productos_json = json.dumps(top_productos_list, default=str)
    ventas_por_sucursal_json = json.dumps(list(ventas_por_sucursal), default=str)

    # --- Contexto final ---
    context = {
        "metricas": {
            "total_ventas": float(metricas['total_ventas']),
            "num_ventas": int(metricas['num_ventas']),
            "ticket_promedio": float(metricas['ticket_promedio']),
            "items_vendidos": int(finanzas['items_vendidos']),
            "productos_unicos": int(finanzas['productos_unicos']),
            "margen_ganancia": round(float(margen), 2)
        },
        # Para renderizado server-side (tabla)
        "top_productos": top_productos_list,
        # Para uso en JS con Chart.js
        "top_productos_json": top_productos_json,
        # Ventas por hora en formato JSON para gráficas
        "ventas_por_hora_json": json.dumps(list(ventas_por_hora), default=str),
        # Ventas por sucursal para gráfico
        "ventas_por_sucursal_json": ventas_por_sucursal_json,
        "actividades_recientes": list(actividades_recientes),
        "sucursales": list(Sucursal.objects.values('id_sucursal', 'nombre')),
        # Datos rápidos para los widgets/gráficos
        "ingresos": float(finanzas['ingresos']),
        "ganancia": float(finanzas['ganancia']),
        "costos": 0.0,
        "filtros": {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "sucursal_id": sucursal_id
        }
    }

    # --- Cachear resultado ---
    cache.set(cache_key, context, CACHE_TTL)

    return render(request, "reportes/dashboard.html", context)



# EXPORTAR A EXCEL
@login_required
def exportar_excel(request):
    """Exporta reporte detallado de ventas a Excel"""
    fecha_fin = request.GET.get("fecha_fin", timezone.now().date())
    fecha_inicio = request.GET.get("fecha_inicio", (timezone.now() - timedelta(days=DEFAULT_DATE_RANGE)).date())
    sucursal_id = request.GET.get("sucursal")

    # Normalizar fechas: aceptar strings o date y convertir a datetimes al inicio/fin del día
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.fromisoformat(fecha_inicio)
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.fromisoformat(fecha_fin)
    if not isinstance(fecha_inicio, datetime):
        fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    if not isinstance(fecha_fin, datetime):
        fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    try:
        if fecha_inicio.tzinfo is None:
            fecha_inicio = timezone.make_aware(fecha_inicio)
        if fecha_fin.tzinfo is None:
            fecha_fin = timezone.make_aware(fecha_fin)
    except Exception:
        pass

    # Incluir estados que representan ventas finalizadas
    ventas = Venta.objects.filter(fecha__range=[fecha_inicio, fecha_fin], estado__in=['completada', 'pagado'])
    if sucursal_id:
        ventas = ventas.filter(sucursal_id=sucursal_id)

    detalles = DetalleVenta.objects.filter(venta__in=ventas)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Hoja 1: Ventas
        df_ventas = pd.DataFrame(list(ventas.values(
            'id_venta', 'fecha', 'total', 'sucursal__nombre', 'cliente__nombre', 'estado'
        )))

        # Si no hay ventas, escribir hoja de 'Sin datos' inmediatamente
        if df_ventas.empty:
            pd.DataFrame([{"Mensaje": "Sin datos disponibles"}]).to_excel(writer, index=False, sheet_name='Ventas')
        else:
            # Nombrar columnas y normalizar fechas antes de escribir
            df_ventas.columns = ['Nro Venta', 'Fecha', 'Total (Bs)', 'Sucursal', 'Cliente', 'Estado']

            # Pandas/openpyxl cannot write timezone-aware datetimes to Excel.
            # Convert any timezone-aware datetimes to naive datetimes in local time,
            # falling back to string if conversion fails.
            if 'Fecha' in df_ventas.columns and not df_ventas['Fecha'].isna().all():
                try:
                    def _to_naive(dt):
                        if pd.isna(dt):
                            return dt
                        try:
                            # If it's timezone-aware, convert to local time then drop tzinfo
                            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                                return timezone.localtime(dt).replace(tzinfo=None)
                        except Exception:
                            pass
                        return dt

                    df_ventas['Fecha'] = df_ventas['Fecha'].apply(_to_naive)
                except Exception:
                    # As a last resort convert datetimes to ISO strings so Excel can store them
                    df_ventas['Fecha'] = df_ventas['Fecha'].astype(str)

            df_ventas.to_excel(writer, index=False, sheet_name='Ventas')


        # Hoja 2: Productos
        df_productos = pd.DataFrame(list(detalles.values(
            'producto__nombre', 'producto__codigo_barras'
        ).annotate(
            cantidad_total=Sum('cantidad'),
            ingreso_total=decimal_sum(F('cantidad') * F('precio_unitario')),
            ganancia_total=Sum('ganancia')
        ).order_by('-cantidad_total')))
        # Asegurar que las columnas numéricas sean float (no objetos/Decimal)
        if not df_productos.empty:
            try:
                for col in ['cantidad_total', 'ingreso_total', 'ganancia_total']:
                    if col in df_productos.columns:
                        df_productos[col] = pd.to_numeric(df_productos[col], errors='coerce').fillna(0).astype(float)

                # Calcular margen (%) solo donde ingreso_total > 0
                df_productos['margen (%)'] = 0.0
                mask = df_productos['ingreso_total'] > 0
                df_productos.loc[mask, 'margen (%)'] = (
                    (df_productos.loc[mask, 'ganancia_total'] / df_productos.loc[mask, 'ingreso_total'] * 100)
                    .round(2)
                )
            except Exception:
                # Fallback: calcular convirtiendo a str para evitar fallos y asignar 0
                df_productos['margen (%)'] = df_productos.get('margen (%)', 0)

            df_productos.columns = ['Producto', 'Código', 'Unidades Vendidas', 'Ingreso Total (Bs)', 'Ganancia (Bs)', 'Margen (%)']
            df_productos.to_excel(writer, index=False, sheet_name='Productos')
        else:
            pd.DataFrame([{"Mensaje": "Sin datos disponibles"}]).to_excel(writer, index=False, sheet_name='Productos')


        # Hoja 3: Finanzas
        finanzas = detalles.aggregate(
            ingresos=Coalesce(decimal_sum(F('cantidad') * F('precio_unitario')), Value(0), output_field=DecimalField()),
            ganancia=Coalesce(Sum('ganancia'), Value(0), output_field=DecimalField()),
            items=Count('id'),
            productos=Count('producto', distinct=True)
        )
        df_fin = pd.DataFrame([{
            "Ingresos Totales (Bs)": finanzas['ingresos'],
            "Ganancia Total (Bs)": finanzas['ganancia'],
            "Margen (%)": round(float(finanzas['ganancia'] / finanzas['ingresos'] * 100), 2)
            if finanzas['ingresos'] > 0 else 0,
            "Items Vendidos": finanzas['items'],
            "Productos Únicos": finanzas['productos']
        }])
        if not df_fin.empty:
            df_fin.to_excel(writer, index=False, sheet_name='Finanzas')
        else:
            pd.DataFrame([{"Mensaje": "Sin datos disponibles"}]).to_excel(writer, index=False, sheet_name='Finanzas')


    output.seek(0)
    filename = f"reporte_ventas_{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    # Registrar metadata del reporte (opción A)
    try:
        sucursal_obj = None
        if sucursal_id:
            sucursal_obj = Sucursal.objects.filter(id_sucursal=sucursal_id).first()
        if not sucursal_obj:
            sucursal_obj = Sucursal.objects.first()
        if sucursal_obj:
            _crear_reporte_si_no_existe('export_general_excel', sucursal_obj)
    except Exception:
        # No queremos que un fallo en el logging del reporte impida la descarga
        pass
    return response
@login_required
def exportar_pdf(request):
    """Genera un reporte PDF de ventas y ganancias"""
    fecha_fin = request.GET.get("fecha_fin", timezone.now().date())
    fecha_inicio = request.GET.get(
        "fecha_inicio", (timezone.now() - timedelta(days=30)).date()
    )
    sucursal_id = request.GET.get("sucursal")

    # Normalizar fechas a datetimes (inicio/fin de día) y hacer aware si es necesario
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.fromisoformat(fecha_inicio)
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.fromisoformat(fecha_fin)
    if not isinstance(fecha_inicio, datetime):
        fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    if not isinstance(fecha_fin, datetime):
        fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    try:
        if fecha_inicio.tzinfo is None:
            fecha_inicio = timezone.make_aware(fecha_inicio)
        if fecha_fin.tzinfo is None:
            fecha_fin = timezone.make_aware(fecha_fin)
    except Exception:
        pass

    ventas = Venta.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin], estado__in=["completada", "pagado"]
    )
    if sucursal_id:
        ventas = ventas.filter(sucursal_id=sucursal_id)

    detalles = DetalleVenta.objects.filter(venta__in=ventas)

  
    # Cálculos principales
   
    finanzas = detalles.aggregate(
        ingresos=Coalesce(decimal_sum(F("cantidad") * F("precio_unitario")), Value(0), output_field=DecimalField()),
        ganancia=Coalesce(Sum("ganancia"), Value(0), output_field=DecimalField()),
        items=Count("id"),
        productos=Count("producto", distinct=True),
    )
    margen = (
        finanzas["ganancia"] / finanzas["ingresos"] * 100
        if finanzas["ingresos"] > 0
        else 0
    )

    productos = (
        detalles.values("producto__nombre", "producto__codigo_barras")
        .annotate(
            cantidad_total=Sum("cantidad"),
            ingreso_total=decimal_sum(F("cantidad") * F("precio_unitario")),
            ganancia_total=Sum("ganancia"),
        )
        .order_by("-ganancia_total")
    )

   
    # Configuración del PDF
   
    response = HttpResponse(content_type="application/pdf")
    filename = f"reporte_ventas_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()

    # Título
    elements.append(Paragraph("<b>Reporte de Ventas y Ganancias</b>", styles["Title"]))
    elements.append(
        Paragraph(f"Periodo: {fecha_inicio} al {fecha_fin}", styles["Normal"])
    )
    elements.append(Spacer(1, 12))

   
    # Métricas financieras
   
    resumen = [
        ["Métrica", "Valor"],
        ["Ingresos Totales (Bs)", f"{finanzas['ingresos']:.2f}"],
        ["Ganancia Total (Bs)", f"{finanzas['ganancia']:.2f}"],
        ["Margen (%)", f"{margen:.2f}%"],
        ["Productos Vendidos", str(finanzas["productos"])],
        ["Items Totales", str(finanzas["items"])],
    ]
    tabla_resumen = Table(resumen, hAlign="LEFT")
    tabla_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004080")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]
        )
    )
    elements.append(tabla_resumen)
    elements.append(Spacer(1, 20))

  
    # Tabla de productos
 
    encabezados = [
        "Producto",
        "Código",
        "Cantidad",
        "Ingreso (Bs)",
        "Ganancia (Bs)",
        "Margen (%)",
    ]
    data_productos = [encabezados]

    for p in productos:
        margen_prod = (
            (p["ganancia_total"] / p["ingreso_total"] * 100)
            if p["ingreso_total"] > 0
            else 0
        )
        data_productos.append(
            [
                p["producto__nombre"],
                p["producto__codigo_barras"],
                int(p["cantidad_total"]),
                f"{p['ingreso_total']:.2f}",
                f"{p['ganancia_total']:.2f}",
                f"{margen_prod:.2f}%",
            ]
        )

    tabla_productos = Table(data_productos, hAlign="LEFT")
    tabla_productos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004080")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]
        )
    )
    elements.append(Paragraph("<b>Detalle de Productos Vendidos</b>", styles["Heading2"]))
    elements.append(tabla_productos)

    
    # Render PDF
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    # Registrar metadata del reporte (opción A)
    try:
        sucursal_obj = None
        if sucursal_id:
            sucursal_obj = Sucursal.objects.filter(id_sucursal=sucursal_id).first()
        if not sucursal_obj:
            sucursal_obj = Sucursal.objects.first()
        if sucursal_obj:
            _crear_reporte_si_no_existe('export_general_pdf', sucursal_obj)
    except Exception:
        pass

    return response

# REPORTE DE GANANCIAS

@login_required
def reporte_ganancias(request):
    """Análisis detallado de ganancias por producto y categoría"""
    fecha_fin = request.GET.get("fecha_fin", timezone.now().date())
    fecha_inicio = request.GET.get("fecha_inicio", (timezone.now() - timedelta(days=DEFAULT_DATE_RANGE)).date())
    sucursal_id = request.GET.get("sucursal")

    # Normalizar fechas a datetimes completos
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.fromisoformat(fecha_inicio)
    else:
        fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.fromisoformat(fecha_fin)
    else:
        fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
    
    # Hacer aware si es necesario
    try:
        if fecha_inicio.tzinfo is None:
            fecha_inicio = timezone.make_aware(fecha_inicio)
        if fecha_fin.tzinfo is None:
            fecha_fin = timezone.make_aware(fecha_fin)
    except Exception:
        pass

    cache_key = f'ganancias_{fecha_inicio}_{fecha_fin}_{sucursal_id}'
    cached = cache.get(cache_key)
    # During development avoid returning stale cache when DEBUG=True
    if cached and not getattr(settings, 'DEBUG', False):
        return render(request, "reportes/ganancias.html", cached)

    # Incluir estados que representan ventas finalizadas
    ventas = Venta.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin], 
        estado__in=['completada', 'pagado']
    )
    if sucursal_id:
        ventas = ventas.filter(sucursal_id=sucursal_id)

    detalles = (
        DetalleVenta.objects.filter(venta__in=ventas)
        .select_related("producto")
        .values('producto__nombre', 'producto__codigo_barras')
        .annotate(
            cantidad_total=Sum('cantidad'),
            ingreso=Sum(F('cantidad') * F('precio_unitario'), output_field=DecimalField()),
            ganancia=Sum('ganancia')
        )
        .order_by('-ganancia')
    )

    # Evaluar queryset y enriquecer con campos derivados para la plantilla
    detalles = list(detalles)
    for p in detalles:
        ingreso = p.get('ingreso') or 0
        ganancia = p.get('ganancia') or 0
        try:
            p['margen_pct'] = (float(ganancia) / float(ingreso) * 100) if ingreso else 0
        except Exception:
            p['margen_pct'] = 0

    metricas = {
        'total_ingresos': sum(d['ingreso'] for d in detalles),
        'ganancia_neta': sum(d['ganancia'] for d in detalles),
        'productos_total': len(detalles)
    }
    metricas['margen_promedio'] = (
        (metricas['ganancia_neta'] / metricas['total_ingresos'] * 100)
        if metricas['total_ingresos'] > 0 else 0
    )

    context = {
        'filtros': {
            'fecha_inicio': fecha_inicio.date() if hasattr(fecha_inicio, 'date') else fecha_inicio,
            'fecha_fin': fecha_fin.date() if hasattr(fecha_fin, 'date') else fecha_fin,
            'sucursal_id': sucursal_id
        },
        'metricas': metricas,
        'productos': detalles,
        'sucursales': Sucursal.objects.all()
    }

    cache.set(cache_key, context, CACHE_TTL)
    return render(request, "reportes/ganancias.html", context)


# CRUD DE REPORTES

def reporte_list(request):
    reportes_qs = Reporte.objects.all().order_by('-Fecha_Reporte')
    # Clasificar tipo para la plantilla
    reportes = []
    for r in reportes_qs:
        tipo_raw = (r.Tipo or '').lower()
        if any(k in tipo_raw for k in ['venta', 'ventas', 'ganancia', 'export_ganancias', 'export_general', 'producto']):
            categoria = 'VENTAS'
        elif 'inventario' in tipo_raw:
            categoria = 'INVENTARIO'
        elif 'alert' in tipo_raw or 'alertas' in tipo_raw:
            categoria = 'ALERTAS'
        else:
            categoria = 'ALERTAS'
        # Attach a transient attribute used by the template
        setattr(r, 'Categoria', categoria)
        reportes.append(r)

    # Paginación simple (10 por página)
    from django.core.paginator import Paginator
    paginator = Paginator(reportes, 10)
    page = request.GET.get('page', 1)
    try:
        reportes_page = paginator.page(page)
    except Exception:
        reportes_page = paginator.page(1)

    if request.user.rol not in ['administrador']:
        messages.error(request, "No tiene permisos para ver reportes")
        return redirect('dashboard')
    else:
        return render(request, "reportes/list.html", {"reportes": reportes_page, 'sucursales': Sucursal.objects.all()})


def reporte_create(request):
    form = ReporteForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("reportes:list")
    return render(request, "reportes/form.html", {"form": form})


def reporte_update(request, pk):
    reporte = get_object_or_404(Reporte, pk=pk)
    form = ReporteForm(request.POST or None, instance=reporte)
    if form.is_valid():
        form.save()
        return redirect("reportes:list")
    return render(request, "reportes/form.html", {"form": form})


def reporte_delete(request, pk):
    reporte = get_object_or_404(Reporte, pk=pk)
    if request.method == "POST":
        reporte.delete()
        return redirect("reportes:list")
    return render(request, "reportes/delete.html", {"reporte": reporte})


@login_required
def reporte_ganancias_sin_perdidas(request):
    """
    Reporte de ganancias de ventas sin pérdidas.
    Muestra todas las ventas pagadas con ganancia positiva (o cero).
    """
    # Filtros opcionales
    fecha_fin = request.GET.get("fecha_fin", timezone.now())
    fecha_inicio = request.GET.get("fecha_inicio", timezone.now() - timedelta(days=DEFAULT_DATE_RANGE))
    sucursal_id = request.GET.get("sucursal")

    # Convertir strings ISO a datetime
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.fromisoformat(fecha_inicio)
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.fromisoformat(fecha_fin)

    # Base queryset: ventas pagadas
    ventas = Venta.objects.filter(
        estado="pagado",
        fecha__range=[fecha_inicio, fecha_fin]
    ).select_related('cliente', 'empleado', 'sucursal')

    if sucursal_id:
        ventas = ventas.filter(sucursal_id=sucursal_id)

    # Detalles con ganancia positiva
    detalles_ganancia = DetalleVenta.objects.filter(
        venta__in=ventas,
        ganancia__gte=0  # Solo ganancias positivas o cero
    ).select_related('venta', 'producto')

    # Resumen
    total_ganancias = detalles_ganancia.aggregate(
        total=Coalesce(Sum('ganancia'), Value(0), output_field=DecimalField())
    )['total'] or Decimal('0.00')

    cantidad_detalles = detalles_ganancia.count()

    # Agrupar por producto para ver cuál genera más ganancia
    productos_ganancia = detalles_ganancia.values(
        'producto__nombre',
        'producto__codigo_barras'
    ).annotate(
        total_ganancia=Coalesce(Sum('ganancia'), Value(0), output_field=DecimalField()),
        cantidad=Count('id'),
        ganancia_promedio=Coalesce(Avg('ganancia'), Value(0), output_field=DecimalField())
    ).order_by('-total_ganancia')[:10]

    sucursales = Sucursal.objects.all()

    # Convertir a JSON para gráficos
    productos_ganancia_json = json.dumps(list(productos_ganancia), default=str)

    context = {
        'detalles': detalles_ganancia[:50],  # Limitar a 50 primeros
        'total_ganancias': total_ganancias,
        'cantidad_detalles': cantidad_detalles,
        'productos_ganancia': productos_ganancia,
        'productos_ganancia_json': productos_ganancia_json,
        'fecha_inicio': fecha_inicio.date(),
        'fecha_fin': fecha_fin.date(),
        'sucursal_id': sucursal_id,
        'sucursales': sucursales,
    }

    return render(request, 'reportes/reporte_ganancias_sin_perdidas.html', context)


@login_required
def reporte_producto_mas_caro_vendido(request):
    """
    Reporte del producto más caro vendido en la farmacia.
    Muestra el producto con el precio unitario más alto en las ventas.
    """
    # Filtros opcionales
    fecha_fin = request.GET.get("fecha_fin", timezone.now())
    fecha_inicio = request.GET.get("fecha_inicio", timezone.now() - timedelta(days=DEFAULT_DATE_RANGE))
    sucursal_id = request.GET.get("sucursal")

    # Convertir strings ISO a datetime
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.fromisoformat(fecha_inicio)
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.fromisoformat(fecha_fin)

    # Base queryset: ventas pagadas
    ventas_pagadas = Venta.objects.filter(
        estado="pagado",
        fecha__range=[fecha_inicio, fecha_fin]
    )

    if sucursal_id:
        ventas_pagadas = ventas_pagadas.filter(sucursal_id=sucursal_id)

    # Detalles de venta ordenados por precio unitario descendente
    detalles_vendidos = DetalleVenta.objects.filter(
        venta__in=ventas_pagadas
    ).select_related('venta', 'producto', 'venta__cliente', 'venta__empleado', 'venta__sucursal').order_by(
        '-precio_unitario'
    )

    # Producto más caro vendido
    producto_mas_caro = detalles_vendidos.first() if detalles_vendidos.exists() else None

    # Top 10 productos más caros vendidos
    top_productos_caros = detalles_vendidos.values(
        'producto__nombre',
        'producto__codigo_barras',
        'producto__descripcion'
    ).annotate(
        precio_max=Max('precio_unitario'),
        veces_vendido=Count('id'),
        total_vendido=Sum(
            ExpressionWrapper(
                F('precio_unitario') * F('cantidad'),
                output_field=DecimalField()
            )
        )
    ).order_by('-precio_max')[:10]

    sucursales = Sucursal.objects.all()

    # Convertir a JSON para gráficos
    top_productos_json = json.dumps(list(top_productos_caros), default=str)

    context = {
        'producto_mas_caro': producto_mas_caro,
        'detalles_vendidos': detalles_vendidos[:20],  # Limitar a 20 primeros
        'top_productos_caros': top_productos_caros,
        'top_productos_json': top_productos_json,
        'fecha_inicio': fecha_inicio.date(),
        'fecha_fin': fecha_fin.date(),
        'sucursal_id': sucursal_id,
        'sucursales': sucursales,
    }

    return render(request, 'reportes/reporte_producto_mas_caro.html', context)


@login_required
def exportar_ganancias_sin_perdidas_excel(request):
    """Exportar reporte de ganancias sin pérdidas a Excel"""
    fecha_fin = request.GET.get("fecha_fin", timezone.now())
    fecha_inicio = request.GET.get("fecha_inicio", timezone.now() - timedelta(days=DEFAULT_DATE_RANGE))
    sucursal_id = request.GET.get("sucursal")

    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.fromisoformat(fecha_inicio)
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.fromisoformat(fecha_fin)

    ventas = Venta.objects.filter(
        estado="pagado",
        fecha__range=[fecha_inicio, fecha_fin]
    ).select_related('cliente', 'empleado', 'sucursal')

    if sucursal_id:
        ventas = ventas.filter(sucursal_id=sucursal_id)

    detalles_ganancia = DetalleVenta.objects.filter(
        venta__in=ventas,
        ganancia__gte=0
    ).select_related('venta', 'producto').values(
        'producto__nombre',
        'producto__codigo_barras',
        'cantidad',
        'precio_unitario',
        'subtotal',
        'ganancia',
        'venta__cliente__nombre',
        'venta__fecha'
    )

    df = pd.DataFrame(list(detalles_ganancia))
    
    if not df.empty:
        df.columns = ['Producto', 'Código', 'Cantidad', 'Precio Unitario', 'Subtotal', 'Ganancia', 'Cliente', 'Fecha']

        # Normalizar datetimes con timezone a naive para Excel
        try:
            def _to_naive(dt):
                if pd.isna(dt):
                    return dt
                try:
                    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                        return timezone.localtime(dt).replace(tzinfo=None)
                except Exception:
                    pass
                return dt

            for col in df.columns:
                try:
                    df[col] = df[col].apply(_to_naive)
                except Exception:
                    # ignore columns that can't be processed
                    pass
        except Exception:
            pass
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Ganancias', index=False)
    
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_ganancias_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    # Registrar metadata del reporte (opción A)
    try:
        sucursal_obj = None
        if sucursal_id:
            sucursal_obj = Sucursal.objects.filter(id_sucursal=sucursal_id).first()
        if not sucursal_obj:
            sucursal_obj = Sucursal.objects.first()
        if sucursal_obj:
            _crear_reporte_si_no_existe('export_ganancias_excel', sucursal_obj)
    except Exception:
        pass

    return response


@login_required
def exportar_producto_mas_caro_excel(request):
    """Exportar reporte de producto más caro a Excel"""
    fecha_fin = request.GET.get("fecha_fin", timezone.now())
    fecha_inicio = request.GET.get("fecha_inicio", timezone.now() - timedelta(days=DEFAULT_DATE_RANGE))
    sucursal_id = request.GET.get("sucursal")

    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.fromisoformat(fecha_inicio)
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.fromisoformat(fecha_fin)

    ventas_pagadas = Venta.objects.filter(
        estado="pagado",
        fecha__range=[fecha_inicio, fecha_fin]
    )

    if sucursal_id:
        ventas_pagadas = ventas_pagadas.filter(sucursal_id=sucursal_id)

    detalles_vendidos = DetalleVenta.objects.filter(
        venta__in=ventas_pagadas
    ).select_related('venta', 'producto', 'venta__cliente', 'venta__sucursal').order_by(
        '-precio_unitario'
    ).values(
        'producto__nombre',
        'producto__codigo_barras',
        'precio_unitario',
        'cantidad',
        'subtotal',
        'venta__cliente__nombre',
        'venta__sucursal__nombre',
        'venta__fecha'
    )

    df = pd.DataFrame(list(detalles_vendidos))
    
    if not df.empty:
        df.columns = ['Producto', 'Código', 'Precio Unitario', 'Cantidad', 'Subtotal', 'Cliente', 'Sucursal', 'Fecha']

        # Normalizar datetimes con timezone a naive para Excel
        try:
            def _to_naive(dt):
                if pd.isna(dt):
                    return dt
                try:
                    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                        return timezone.localtime(dt).replace(tzinfo=None)
                except Exception:
                    pass
                return dt

            for col in df.columns:
                try:
                    df[col] = df[col].apply(_to_naive)
                except Exception:
                    pass
        except Exception:
            pass
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Productos Caros', index=False)
    
    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte_producto_caro_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    # Registrar metadata del reporte (opción A)
    try:
        sucursal_obj = None
        if sucursal_id:
            sucursal_obj = Sucursal.objects.filter(id_sucursal=sucursal_id).first()
        if not sucursal_obj:
            sucursal_obj = Sucursal.objects.first()
        if sucursal_obj:
            _crear_reporte_si_no_existe('export_producto_caro_excel', sucursal_obj)
    except Exception:
        pass

    return response


