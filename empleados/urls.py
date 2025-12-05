from django.urls import path
from . import views

app_name = "empleados"

urlpatterns = [
    path("", views.empleado_list, name="list"),
    path("nuevo/", views.empleado_create, name="create"),
    path("<str:pk>/editar/", views.empleado_update, name="update"),
    path("<str:pk>/eliminar/", views.empleado_delete, name="delete"),

]
