from django.core.exceptions import ValidationError
from django.db import models
from urbanizaciones.models import Urbanizacion


class Pista(models.Model):
    urbanizacion = models.ForeignKey(Urbanizacion, on_delete=models.CASCADE, related_name='pistas')
    nombre = models.CharField(max_length=100, default='Pista 1')
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ('urbanizacion', 'nombre')
        ordering = ['urbanizacion', 'nombre']

    def clean(self):
        if not self.pk:
            existentes = Pista.objects.filter(urbanizacion=self.urbanizacion).count()
            if existentes >= self.urbanizacion.num_pistas:
                raise ValidationError(
                    f'{self.urbanizacion} ya tiene el máximo de {self.urbanizacion.num_pistas} '
                    f'pista(s) configurado. Sube ese número en los ajustes de la urbanización '
                    f'antes de añadir otra.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} — {self.urbanizacion}'
