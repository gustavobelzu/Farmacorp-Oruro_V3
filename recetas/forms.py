from django import forms
from django.forms import inlineformset_factory
from .models import Receta, DetalleReceta

class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = ['cliente', 'empleado', 'Matricula_medico', 'fecha_emision', 'Medicamento', 'Cantidad']
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'Medicamento': forms.TextInput(attrs={'class': 'form-control'}),
            'Cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class DetalleRecetaForm(forms.ModelForm):
    class Meta:
        model = DetalleReceta
        fields = ['producto', 'dosis', 'frecuencia', 'duracion', 'instrucciones']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'dosis': forms.TextInput(attrs={'class': 'form-control'}),
            'frecuencia': forms.TextInput(attrs={'class': 'form-control'}),
            'duracion': forms.TextInput(attrs={'class': 'form-control'}),
            'instrucciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

# Formset para agregar múltiples detalles a una receta
DetalleRecetaFormSet = inlineformset_factory(
    Receta,
    DetalleReceta,
    form=DetalleRecetaForm,
    extra=3,  # Mostrar 3 formularios en blanco por defecto
    can_delete=True  # Permitir eliminar detalles
)
