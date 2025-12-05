from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Usuario
from empleados.models import Empleado
from clientes.models import Cliente
from django.utils.text import slugify

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

class UsuarioCreateForm(UserCreationForm):
    username = forms.CharField(required=False)
    ci_empleado = forms.ModelChoiceField(queryset=Empleado.objects.all(), required=False)
    ci_cliente = forms.ModelChoiceField(queryset=Cliente.objects.all(), required=False)

    class Meta:
        model = Usuario
        fields = ["username", "email", "password1", "password2", "ci_empleado", "ci_cliente"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        ci_empleado = cleaned_data.get('ci_empleado')
        ci_cliente = cleaned_data.get('ci_cliente')

        # Si no se proporcionó username, generarlo a partir de la relación
        if not username:
            base = None
            if ci_empleado:
                base = f"emp_{ci_empleado.ci}"
            elif ci_cliente:
                base = f"cli_{ci_cliente.ci_cliente}"

            if base:
                # Normalizar y asegurar unicidad
                base_slug = slugify(str(base))
                candidate = base_slug
                i = 1
                while Usuario.objects.filter(username=candidate).exists():
                    candidate = f"{base_slug}_{i}"
                    i += 1
                cleaned_data['username'] = candidate

        return cleaned_data

