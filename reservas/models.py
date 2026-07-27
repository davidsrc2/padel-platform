from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta

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
        # Si pista/usuario/fecha/horas no están fijados (p. ej. porque el
        # campo "pista" falló su propia validación en el ModelForm — un
        # intento de reservar una pista de otra urbanización), no hay nada
        # que validar aquí: clean_fields() ya reporta el error de ese campo.
        if not self.pista_id or not self.usuario_id or self.hora_inicio is None or self.hora_fin is None or self.fecha is None:
            return

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


def validar_set(juegos_a, juegos_b, es_super_tiebreak=False):
    """Reglas de un set de pádel: a 6 con 2 de ventaja, o 7 (7-5 o 7-6 de
    tie-break). El 3er set puede jugarse como súper tie-break a 10 con 2 de
    ventaja en su lugar."""
    if juegos_a == juegos_b:
        raise ValidationError(f'Un set no puede terminar en empate ({juegos_a}-{juegos_b}).')
    ganador, perdedor = max(juegos_a, juegos_b), min(juegos_a, juegos_b)
    if es_super_tiebreak:
        if ganador < 10 or ganador - perdedor < 2:
            raise ValidationError(
                f'Súper tie-break inválido ({juegos_a}-{juegos_b}): hay que llegar a 10 con 2 de ventaja.'
            )
    else:
        valido = (ganador == 6 and perdedor <= 4) or (ganador == 7 and perdedor in (5, 6))
        if not valido:
            raise ValidationError(f'Marcador de set inválido: {juegos_a}-{juegos_b}.')


class ResultadoPartido(models.Model):
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_CONFIRMADO = 'confirmado'
    ESTADO_DISPUTADO = 'disputado'

    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente de confirmación'),
        (ESTADO_CONFIRMADO, 'Confirmado'),
        (ESTADO_DISPUTADO, 'Disputado'),
    ]

    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='resultado')
    equipo_a = models.ManyToManyField(Usuario, related_name='resultados_equipo_a')
    equipo_b = models.ManyToManyField(Usuario, related_name='resultados_equipo_b')
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    creado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='resultados_creados')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    confirmado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='resultados_confirmados'
    )
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Resultado de partido'
        verbose_name_plural = 'Resultados de partido'
        ordering = ['-reserva__fecha', '-reserva__hora_inicio']

    def clean(self):
        if not self.reserva_id:
            return
        if self.reserva.estado != Reserva.ESTADO_CONFIRMADA:
            raise ValidationError('Solo se puede registrar el resultado de una reserva confirmada.')
        fin_dt = timezone.make_aware(datetime.combine(self.reserva.fecha, self.reserva.hora_fin))
        if fin_dt > timezone.now():
            raise ValidationError('No puedes registrar el resultado de un partido que todavía no ha terminado.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def sets_ganados(self, equipo):
        campo = 'gano_equipo_a' if equipo == 'A' else 'gano_equipo_b'
        return sum(1 for s in self.sets.all() if getattr(s, campo))

    @property
    def ganador(self):
        ganados_a = self.sets_ganados('A')
        ganados_b = self.sets_ganados('B')
        if ganados_a > ganados_b:
            return 'A'
        if ganados_b > ganados_a:
            return 'B'
        return None

    def gano(self, usuario):
        """True/False/None (no jugó este partido) para saber si `usuario` ganó."""
        ganador = self.ganador
        if ganador is None:
            return None
        equipo_ganador = self.equipo_a if ganador == 'A' else self.equipo_b
        if equipo_ganador.filter(pk=usuario.pk).exists():
            return True
        equipo_perdedor = self.equipo_b if ganador == 'A' else self.equipo_a
        if equipo_perdedor.filter(pk=usuario.pk).exists():
            return False
        return None

    def __str__(self):
        return f'Resultado de {self.reserva}'


class SetResultado(models.Model):
    resultado = models.ForeignKey(ResultadoPartido, on_delete=models.CASCADE, related_name='sets')
    numero = models.PositiveSmallIntegerField()
    juegos_equipo_a = models.PositiveSmallIntegerField()
    juegos_equipo_b = models.PositiveSmallIntegerField()
    es_super_tiebreak = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Set'
        verbose_name_plural = 'Sets'
        ordering = ['numero']
        unique_together = ('resultado', 'numero')

    def clean(self):
        validar_set(self.juegos_equipo_a, self.juegos_equipo_b, self.es_super_tiebreak)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def gano_equipo_a(self):
        return self.juegos_equipo_a > self.juegos_equipo_b

    @property
    def gano_equipo_b(self):
        return self.juegos_equipo_b > self.juegos_equipo_a

    def __str__(self):
        return f'{self.juegos_equipo_a}-{self.juegos_equipo_b}'
