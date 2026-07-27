from django import forms
from .models import Pista


class PistaForm(forms.ModelForm):
    class Meta:
        model = Pista
        fields = ['nombre']

    def __init__(self, *args, urbanizacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Hay que fijar la urbanización antes de is_valid(): Pista.clean()
        # la necesita para contar las pistas existentes, y ModelForm valida
        # el modelo (full_clean) antes de que la vista pueda asignarla.
        if urbanizacion:
            self.instance.urbanizacion = urbanizacion
