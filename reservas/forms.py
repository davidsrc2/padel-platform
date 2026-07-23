from django import forms
from .models import Reserva
from datetime import datetime, timedelta
from django.utils import timezone


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

        if pista and fecha and hora_inicio:
            urb = pista.urbanizacion
            from datetime import timedelta as td
            duracion = td(minutes=urb.duracion_franja_minutos)
            inicio_dt = datetime.combine(fecha, hora_inicio)
            hora_fin = (inicio_dt + duracion).time()
            cleaned['hora_fin'] = hora_fin

        return cleaned

    def save(self, commit=True):
        reserva = super().save(commit=False)
        urb = reserva.pista.urbanizacion
        from datetime import timedelta as td
        duracion = td(minutes=urb.duracion_franja_minutos)
        inicio_dt = datetime.combine(reserva.fecha, reserva.hora_inicio)
        reserva.hora_fin = (inicio_dt + duracion).time()
        reserva.usuario = self.usuario
        reserva.full_clean()
        if commit:
            reserva.save()
        return reserva
