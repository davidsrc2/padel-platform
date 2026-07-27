from django.core.exceptions import ValidationError
from django.db import models


class Urbanizacion(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300)
    num_pistas = models.PositiveSmallIntegerField(default=1)
    hora_apertura = models.TimeField(default='08:00')
    hora_cierre = models.TimeField(default='22:00')
    duracion_franja_minutos = models.PositiveSmallIntegerField(default=90)
    max_reservas_por_vivienda = models.PositiveSmallIntegerField(default=1)
    antelacion_maxima_dias = models.PositiveSmallIntegerField(default=7)
    cancelacion_minima_horas = models.PositiveSmallIntegerField(default=2)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Urbanización'
        verbose_name_plural = 'Urbanizaciones'

    def clean(self):
        if self.pk and self.num_pistas < self.pistas.count():
            raise ValidationError(
                f'No puedes bajar el número de pistas a {self.num_pistas}: '
                f'ya hay {self.pistas.count()} pista(s) creada(s). Elimínalas primero.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre
