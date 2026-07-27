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


class BloqueoPista(models.Model):
    """Franja bloqueada por mantenimiento u otro motivo: nadie puede reservarla."""

    pista = models.ForeignKey(Pista, on_delete=models.CASCADE, related_name='bloqueos')
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    motivo = models.CharField(max_length=200, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bloqueo de pista'
        verbose_name_plural = 'Bloqueos de pista'
        ordering = ['fecha', 'hora_inicio']

    def clean(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio debe ser anterior a la hora de fin.')

        # Import diferido: reservas.models importa pistas.models, un import
        # a nivel de módulo aquí crearía un ciclo.
        from reservas.models import Reserva

        conflicto = Reserva.objects.filter(
            pista=self.pista,
            fecha=self.fecha,
            estado=Reserva.ESTADO_CONFIRMADA,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exists()
        if conflicto:
            raise ValidationError(
                'Ya hay una reserva confirmada en ese horario. Cancélala antes de bloquear la franja.'
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.pista} · {self.fecha} {self.hora_inicio}–{self.hora_fin}'
