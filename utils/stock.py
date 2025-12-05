from productos.models import Producto
from django.db.models import Sum
#Actualizar stock Automaticamente
def actualizar_stock_producto(producto):
    from inventario.models import Inventario  # ← Importación local, evita el ciclo
    total = Inventario.objects.filter(producto=producto, estado=True).aggregate(s=Sum("cantidad"))["s"] or 0
    producto.stock = total
    producto.save()