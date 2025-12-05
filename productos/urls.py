from django.urls import path
from . import views

app_name = "productos"

urlpatterns = [
    path('', views.producto_list, name="list"),
    path("editar/<str:pk>/", views.producto_update, name="editar"),
    path("eliminar/<str:pk>/", views.producto_delete, name="eliminar"),
    path('detalle/<str:codigo>/', views.producto_detail, name='detalle'),
    path("crear/", views.producto_create, name="producto_create"),
    # Proveedores
    path("proveedor/", views.proveedor_list, name="listp"),
    path("proveedor/crear/", views.proveedor_create, name="proveedor_create"),
    path("proveedor/editar/<int:pk>/", views.proveedor_update, name="editarp"),
    path("proveedor/eliminar/<int:pk>/", views.proveedor_delete, name="eliminarp"),
    #Compras
    path('compras/', views.compra_list, name='listc'),
    path('compras/nueva/', views.compra_create, name='compra_create'),
    path('compras/editar/<int:pk>/', views.compra_update, name='updatec'),
    path('compras/eliminar/<int:pk>/', views.compra_delete, name='deletec'),
]


