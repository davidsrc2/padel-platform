from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario
from viviendas.models import Vivienda, Portal
from urbanizaciones.models import Urbanizacion


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label='Nombre', max_length=150, required=True)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=True)
    email = forms.EmailField(label='Email', required=True)
    telefono = forms.CharField(label='Teléfono', max_length=20, required=False)
    urbanizacion = forms.ModelChoiceField(
        queryset=Urbanizacion.objects.all(),
        label='Urbanización',
        empty_label='Selecciona tu urbanización',
    )
    portal = forms.ModelChoiceField(
        queryset=Portal.objects.none(),
        label='Portal',
        empty_label='Selecciona el portal',
    )
    vivienda = forms.ModelChoiceField(
        queryset=Vivienda.objects.none(),
        label='Vivienda (piso)',
        empty_label='Selecciona tu piso',
    )

    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono',
                  'urbanizacion', 'portal', 'vivienda', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'urbanizacion' in self.data:
            try:
                urb_id = int(self.data.get('urbanizacion'))
                self.fields['portal'].queryset = Portal.objects.filter(urbanizacion_id=urb_id)
            except (ValueError, TypeError):
                pass
        if 'portal' in self.data:
            try:
                portal_id = int(self.data.get('portal'))
                self.fields['vivienda'].queryset = Vivienda.objects.filter(portal_id=portal_id)
            except (ValueError, TypeError):
                pass

    def save(self, commit=True):
        user = super().save(commit=False)
        user.vivienda = self.cleaned_data['vivienda']
        user.telefono = self.cleaned_data.get('telefono', '')
        user.aprobado = False
        if commit:
            user.save()
        return user
