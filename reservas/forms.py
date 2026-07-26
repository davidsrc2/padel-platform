from django import forms
from .models import Reserva
from datetime import datetime, timedelta


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['pista', 'fecha', 'hora_inicio']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio': forms.HiddenInput(),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if usuario and usuario.urbanizacion:
            self.fields['pista'].queryset = usuario.urbanizacion.pistas.filter(activa=True)

    def clean(self):
        cleaned = super().clean()
        pista = cleaned.get('pista')
        fecha = cleaned.get('fecha')
        hora_inicio = cleaned.get('hora_inicio')

        # El modelo valida su propio estado en clean(), que se ejecuta sobre
        # self.instance antes de que ModelForm asigne los campos que no están
        # en Meta.fields (usuario, hora_fin) — hay que fijarlos aquí a mano.
        if self.usuario:
            self.instance.usuario = self.usuario

        if pista and fecha and hora_inicio:
            urb = pista.urbanizacion
            duracion = timedelta(minutes=urb.duracion_franja_minutos)
            inicio_dt = datetime.combine(fecha, hora_inicio)
            hora_fin = (inicio_dt + duracion).time()
            cleaned['hora_fin'] = hora_fin
            self.instance.hora_fin = hora_fin

        return cleaned

    def save(self, commit=True):
        reserva = super().save(commit=False)
        reserva.usuario = self.usuario
        if commit:
            reserva.save()
        return reserva
