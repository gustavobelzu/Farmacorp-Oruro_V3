from django import forms
from .models import Inventario
from productos.models import Producto
from farmacia.models import Sucursal

class InventarioForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mejorar los campos select
        self.fields['producto'].widget.attrs.update({
            'class': 'form-select',
            'data-live-search': 'true'
        })
        self.fields['sucursal'].widget.attrs.update({
            'class': 'form-select'
        })
        
        # Añadir clases Bootstrap y placeholders
        self.fields['cantidad'].widget.attrs.update({
            'class': 'form-control',
            'min': '0',
            'placeholder': 'Ingrese la cantidad'
        })
        self.fields['stock_minimo'].widget.attrs.update({
            'class': 'form-control',
            'min': '0',
            'placeholder': 'Ingrese el stock mínimo'
        })
        self.fields['ubicacion'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingrese la ubicación'
        })
        
        # Mostrar todos los productos
        self.fields['producto'].queryset = Producto.objects.all()

        # Mejorar la visualización de productos en el select
        self.fields['producto'].label_from_instance = lambda obj: f"{obj.nombre} (Stock: {obj.stock})"
        
        # Añadir help texts útiles
        self.fields['stock_minimo'].help_text = 'Cantidad mínima antes de generar alertas'
        self.fields['ubicacion'].help_text = 'Ubicación física en el almacén'

    class Meta:
        model = Inventario
        fields = ['producto', 'sucursal', 'cantidad', 'stock_minimo', 'ubicacion']
        labels = {
            'producto': 'Producto',
            'sucursal': 'Sucursal',
            'cantidad': 'Cantidad',
            'stock_minimo': 'Stock Mínimo',
            'ubicacion': 'Ubicación'
        }
