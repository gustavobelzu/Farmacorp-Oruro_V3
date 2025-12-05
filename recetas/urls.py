from django.urls import path
from . import views

app_name = "recetas"

urlpatterns = [
    # Rutas para Recetas
    path("listar/", views.receta_list, name="list"),
    path("mis-recetas/", views.mis_recetas, name="mis_recetas"),
    path("crear/", views.receta_create, name="create"),
    path("editar/<int:pk>/", views.receta_update, name="editar"),
    path("eliminar/<int:pk>/", views.receta_delete, name="eliminar"),
    path("detalle/<int:pk>/", views.receta_detalle, name="detalle"),
    
    # Rutas para DetalleReceta
    path("detalle/<int:receta_id>/agregar/", views.agregar_detalle, name="agregar_detalle"),
    path("detalle/editar/<int:pk>/", views.detalle_update, name="detalle_editar"),
    path("detalle/eliminar/<int:pk>/", views.detalle_delete, name="detalle_eliminar"),
]
