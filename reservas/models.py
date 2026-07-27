from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from pistas.models import BloqueoPista, Pista
from accounts.models import Usuario


class Reserva(models.Model):
    ESTADO_CONFIRMADA = 'confirmada'
    ESTADO_CANCELADA = 'cancelada'

    ESTADOS = [
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    pista = models.ForeignKey(Pista, on_delete=models.CASCADE, related_name='reservas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='reservas')
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_CONFIRMADA)
    companeros = models.CharField('Con quién juegas', max_length=200, blank=True)
    recordatorio_enviado = models.BooleanField(default=False)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'hora_inicio']

    @property
    def urbanizacion(self):
        return self.pista.urbanizacion

    def clean(self):
        urb = self.pista.urbanizacion

        # Fecha en rango permitido
        hoy = timezone.localdate()
        max_fecha = hoy + timedelta(days=urb.antelacion_maxima_dias)
        if self.fecha < hoy:
            raise ValidationError('No puedes reservar en fechas pasadas.')
        if self.fecha > max_fecha:
            raise ValidationError(
                f'Solo puedes reservar con un máximo de {urb.antelacion_maxima_dias} días de antelación.'
            )

        # Horario dentro del permitido por la urbanización
        if self.hora_inicio < urb.hora_apertura or self.hora_fin > urb.hora_cierre:
            raise ValidationError('La reserva está fuera del horario permitido.')

        if self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio debe ser anterior a la hora de fin.')

        # Solapamiento con otras reservas confirmadas
        solapadas = Reserva.objects.filter(
            pista=self.pista,
            fecha=self.fecha,
            estado=self.ESTADO_CONFIRMADA,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        )
        if self.pk:
            solapadas = solapadas.exclude(pk=self.pk)
        if solapadas.exists():
            raise ValidationError('Esa franja ya está ocupada.')

        # Bloqueada por mantenimiento
        bloqueada = BloqueoPista.objects.filter(
            pista=self.pista,
            fecha=self.fecha,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
        ).exists()
        if bloqueada:
            raise ValidationError('Esa franja está bloqueada por mantenimiento.')

        # Límite de reservas activas por vivienda
        if self.usuario.vivienda and self.estado == self.ESTADO_CONFIRMADA:
            vivienda = self.usuario.vivienda
            activas = Reserva.objects.filter(
                usuario__vivienda=vivienda,
                pista__urbanizacion=urb,
                estado=self.ESTADO_CONFIRMADA,
                fecha__gte=timezone.localdate(),
            )
            if self.pk:
                activas = activas.exclude(pk=self.pk)
            if activas.count() >= urb.max_reservas_por_vivienda:
                raise ValidationError(
                    f'Tu vivienda ya tiene el máximo de {urb.max_reservas_por_vivienda} reserva(s) activa(s).'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def puede_cancelar(self):
        urb = self.urbanizacion
        ahora = timezone.localtime()
        inicio_dt = timezone.make_aware(
            timezone.datetime.combine(self.fecha, self.hora_inicio)
        )
        margen = timedelta(hours=urb.cancelacion_minima_horas)
        return ahora + margen <= inicio_dt

    def __str__(self):
        return f'{self.pista} · {self.fecha} {self.hora_inicio}–{self.hora_fin} ({self.usuario})'
