from django import forms
from .models import BloqueoPista, Pista


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


class BloqueoPistaForm(forms.ModelForm):
    class Meta:
        model = BloqueoPista
        fields = ['fecha', 'hora_inicio', 'hora_fin', 'motivo']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time'}),
            'motivo': forms.TextInput(attrs={'placeholder': 'Motivo (opcional)'}),
        }

    def __init__(self, *args, pista=None, **kwargs):
        super().__init__(*args, **kwargs)
        if pista:
            self.instance.pista = pista
