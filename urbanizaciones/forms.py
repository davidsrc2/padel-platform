from django import forms
from .models import Urbanizacion


class UrbanizacionForm(forms.ModelForm):
    class Meta:
        model = Urbanizacion
        fields = [
            'nombre', 'direccion', 'num_pistas',
            'hora_apertura', 'hora_cierre', 'duracion_franja_minutos',
            'max_reservas_por_vivienda', 'antelacion_maxima_dias', 'cancelacion_minima_horas',
        ]
        widgets = {
            'hora_apertura': forms.TimeInput(attrs={'type': 'time'}),
            'hora_cierre': forms.TimeInput(attrs={'type': 'time'}),
        }
        labels = {
            'num_pistas': 'Número de pistas',
            'duracion_franja_minutos': 'Duración de cada franja (minutos)',
            'max_reservas_por_vivienda': 'Máx. reservas activas por vivienda',
            'antelacion_maxima_dias': 'Antelación máxima de reserva (días)',
            'cancelacion_minima_horas': 'Margen mínimo para cancelar (horas)',
        }
