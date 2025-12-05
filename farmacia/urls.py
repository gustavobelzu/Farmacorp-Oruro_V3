from django.urls import path
from . import views

app_name = "farmacia"

urlpatterns = [
    # Farmacia
    path("farmacias/", views.farmacia_list, name="list"),
    path("farmacias/nueva/", views.farmacia_create, name="create"),
    path("farmacias/<int:pk>/editar/", views.farmacia_update, name="updatef"),
    path("farmacias/<int:pk>/eliminar/", views.farmacia_delete, name="deletef"),

    # Sucursal
    path("sucursales/", views.sucursal_list, name="listf"),
    path("sucursales/nueva/", views.sucursal_create, name="createf"),
    path("sucursales/<int:pk>/editar/", views.sucursal_update, name="update"),
    path("sucursales/<int:pk>/eliminar/", views.sucursal_delete, name="delete"),
]
