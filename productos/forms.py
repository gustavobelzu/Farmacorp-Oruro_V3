from django import forms
from .models import Producto
from .models import Proveedor,Compra

class ProveedorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mejorar los campos con clases y atributos Bootstrap
        self.fields['nombre'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nombre del proveedor',
            'autofocus': True
        })
        
        self.fields['telefono'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '+591XXXXXXXX',
            'pattern': '^\+?1?\d{9,15}$'
        })
        
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'ejemplo@dominio.com'
        })
        
        self.fields['direccion'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Dirección completa',
            'rows': '3'
        })
        
        self.fields['estado'].widget.attrs.update({
            'class': 'form-check-input'
        })

    class Meta:
        model = Proveedor
        fields = ['nombre', 'telefono', 'email', 'direccion', 'estado']
        labels = {
            'nombre': 'Nombre del Proveedor',
            'telefono': 'Teléfono',
            'email': 'Correo Electrónico',
            'direccion': 'Dirección',
            'estado': 'Activo'
        }
        help_texts = {
            'nombre': 'Ingrese el nombre completo del proveedor',
            'telefono': 'Formato: +591XXXXXXXX',
            'email': 'Correo electrónico de contacto principal',
            'direccion': 'Dirección física del proveedor',
            'estado': 'Indica si el proveedor está activo en el sistema'
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = "__all__"

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['producto', 'precio_compra', 'cantidad']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }