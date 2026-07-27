from django import forms
from .models import Portal, Vivienda


class PortalForm(forms.ModelForm):
    class Meta:
        model = Portal
        fields = ['nombre']
        labels = {'nombre': 'Nombre del portal'}

    def __init__(self, *args, urbanizacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Necesario antes de is_valid(): validate_unique() comprueba
        # (urbanizacion, nombre), y sin esto comprobaría contra urbanizacion=None.
        if urbanizacion:
            self.instance.urbanizacion = urbanizacion


class ViviendaForm(forms.ModelForm):
    class Meta:
        model = Vivienda
        fields = ['piso', 'puerta']

    def __init__(self, *args, portal=None, **kwargs):
        super().__init__(*args, **kwargs)
        if portal:
            self.instance.portal = portal
