from django import forms
from .models import Alerta

class AlertaForm(forms.ModelForm):
    class Meta:
        model = Alerta
        fields = "__all__"
