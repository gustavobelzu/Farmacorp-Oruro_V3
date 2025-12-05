# alertas/urls.py
from django.urls import path
from . import views

app_name = "alertas"

urlpatterns = [
    path('', views.lista_alertas, name='list'),
    path('api/', views.api_alertas, name='api_alertas'),
]

