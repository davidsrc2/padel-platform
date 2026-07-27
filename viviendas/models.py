from django.db import models
from urbanizaciones.models import Urbanizacion


class Portal(models.Model):
    urbanizacion = models.ForeignKey(Urbanizacion, on_delete=models.CASCADE, related_name='portales')
    nombre = models.CharField(max_length=50)

    class Meta:
        unique_together = ('urbanizacion', 'nombre')
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Portal {self.nombre} — {self.urbanizacion}'


class Vivienda(models.Model):
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name='viviendas')
    piso = models.CharField(max_length=10)
    puerta = models.CharField(max_length=5, blank=True)

    class Meta:
        unique_together = ('portal', 'piso', 'puerta')
        ordering = ['portal', 'piso', 'puerta']

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def urbanizacion(self):
        return self.portal.urbanizacion

    def __str__(self):
        puerta = f'-{self.puerta}' if self.puerta else ''
        return f'Portal {self.portal.nombre}, {self.piso}{puerta}'
