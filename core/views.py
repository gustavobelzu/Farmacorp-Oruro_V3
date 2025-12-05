from django.shortcuts import render
from ventas.models import Venta
from clientes.models import Cliente
from productos.models import Producto
from alertas.models import Alerta
from django.db.models import Sum
import io
import calendar
import matplotlib.pyplot as plt
from django.http import HttpResponse
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


def dashboard(request):
    # Datos resumen
    total_ventas = Venta.objects.aggregate(Sum("total"))["total__sum"] or 0
    total_clientes = Cliente.objects.count()
    total_productos = Producto.objects.count()
    total_alertas = Alerta.objects.count()

    # Ventas por mes
    ventas_mensuales = Venta.objects.values_list("fecha__month").annotate(total=Sum("total"))
    meses = [calendar.month_name[m[0]] for m in ventas_mensuales]
    ventas = [m[1] for m in ventas_mensuales]

    # Stock productos
    productos = list(Producto.objects.values_list("nombre", flat=True)[:5])
    stock = list(Producto.objects.values_list("stock", flat=True)[:5])

    context = {
        "total_ventas": total_ventas,
        "total_clientes": total_clientes,
        "total_productos": total_productos,
        "total_alertas": total_alertas,
        "meses": meses,
        "ventas": ventas,
        "productos": productos,
        "stock": stock,
    }
    return render(request, "core/dashboard.html", context)


def export_dashboard_excel(request):
    ventas_mensuales = Venta.objects.values_list("fecha__month").annotate(total=Sum("total"))
    meses = [calendar.month_name[m[0]] for m in ventas_mensuales]
    ventas = [m[1] for m in ventas_mensuales]

    productos = list(Producto.objects.values_list("nombre", flat=True)[:5])
    stock = list(Producto.objects.values_list("stock", flat=True)[:5])

    # Crear DataFrame
    df = pd.DataFrame({
        "Mes": meses,
        "Ventas": ventas
    })

    df_stock = pd.DataFrame({
        "Producto": productos,
        "Stock": stock
    })

    with io.BytesIO() as buffer:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Ventas", index=False)
            df_stock.to_excel(writer, sheet_name="Inventario", index=False)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = 'attachment; filename="dashboard.xlsx"'
        return response


def export_dashboard_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="dashboard.pdf"'

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 750, "Reporte Dashboard Farmacorp")

    # Dibujar gráfico ventas
    ventas_mensuales = Venta.objects.values_list("fecha__month").annotate(total=Sum("total"))
    meses = [calendar.month_name[m[0]] for m in ventas_mensuales]
    ventas = [m[1] for m in ventas_mensuales]

    plt.figure(figsize=(5, 3))
    plt.plot(meses, ventas, marker="o", color="blue")
    plt.title("Ventas Mensuales")
    plt.xlabel("Mes")
    plt.ylabel("Total Ventas")

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="PNG")
    img_buffer.seek(0)
    p.drawImage(img_buffer, 50, 500, width=500, height=200)

    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
