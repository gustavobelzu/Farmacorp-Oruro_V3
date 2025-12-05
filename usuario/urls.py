from django.urls import path
from . import views

app_name = "usuario"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.registrar_usuario, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path('editar/<int:pk>/', views.editar_usuario, name='editar'), # Edición de usuario
    path('eliminar/<int:pk>/', views.eliminar_usuario, name='eliminar'),
    path('', views.usuario_list, name='list'),  
]
