# ventas/urls.py
from django.urls import path
from . import views

app_name = "ventas"
urlpatterns = [
    # CRUD
    path('', views.venta_list, name='venta_list'),
    path('crear/', views.crear_venta, name='venta_create'),
    path('editar/<int:pk>/', views.venta_update, name='venta_update'),
    path('eliminar/<int:pk>/', views.venta_delete, name='venta_delete'),

    # Validación y recibos
    
    path('<int:pk>/validar/', views.validar_venta, name='venta_validar'),
    path('<int:pk>/recibo/', views.ReciboExtendidoView.as_view(), name='venta_recibo'),

    # POS
    path('pos/', views.pos, name='venta_pos'),

    # detalle
    path('<int:pk>/detalle/', views.detalle_venta, name='venta_detalle'),

    # API
    path('api/verificar_total/', views.api_verificar_total, name='api_verificar_total'),
    path("clientes/buscar/", views.buscar_clientes, name="buscar_clientes"),

]
