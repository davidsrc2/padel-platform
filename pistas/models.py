from django.db import models
from urbanizaciones.models import Urbanizacion


class Pista(models.Model):
    urbanizacion = models.ForeignKey(Urbanizacion, on_delete=models.CASCADE, related_name='pistas')
    nombre = models.CharField(max_length=100, default='Pista 1')
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ('urbanizacion', 'nombre')
        ordering = ['urbanizacion', 'nombre']

    def __str__(self):
        return f'{self.nombre} — {self.urbanizacion}'
