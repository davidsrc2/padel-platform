from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import Usuario


class Seguimiento(models.Model):
    """Un vecino sigue a otro. Solo entre vecinos de la misma urbanización
    (el límite de tenant es también el límite del grafo social)."""

    seguidor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='siguiendo')
    seguido = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='seguidores')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Seguimiento'
        verbose_name_plural = 'Seguimientos'
        constraints = [
            models.UniqueConstraint(fields=['seguidor', 'seguido'], name='seguimiento_unico'),
        ]
        ordering = ['-creado']

    def clean(self):
        if not self.seguidor_id or not self.seguido_id:
            return
        if self.seguidor_id == self.seguido_id:
            raise ValidationError('No puedes seguirte a ti mismo.')
        if self.seguidor.urbanizacion != self.seguido.urbanizacion:
            raise ValidationError('Solo puedes seguir a vecinos de tu propia urbanización.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.seguidor} sigue a {self.seguido}'
