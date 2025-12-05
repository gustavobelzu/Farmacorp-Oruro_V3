from django import forms
from clientes.models import Cliente
from inventario.models import Inventario

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['cantidad', 'estado', 'stock_minimo']