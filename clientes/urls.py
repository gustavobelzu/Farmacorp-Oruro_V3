from django.urls import path
from . import views

app_name = "clientes"

urlpatterns = [
    # Vistas administrativas
    path("", views.cliente_list, name="list"),
    path("crear/", views.cliente_create, name="create"),
    path("editar/<str:pk>/", views.cliente_update, name="update"),
    path("eliminar/<str:pk>/", views.cliente_delete, name="delete"),
    
    # Vistas para clientes
    path("mi-historial/", views.historial_cliente, name="mi_historial"),
    path("historial/<str:ci_cliente>/", views.historial_cliente, name="historial"),
    
    # APIs
    path("api/top_clientes/", views.api_clientes_top, name="api_top_clientes"),
]


