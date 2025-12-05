from django import forms
from .models import Empleado

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = "__all__"
        widgets = {
            "cargo": forms.Select(attrs={"class": "form-control"}),
            # otros campos...
        }
