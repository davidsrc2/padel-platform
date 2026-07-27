import os
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from reservas.emails import enviar_recordatorio_reserva
from reservas.models import Reserva


class Command(BaseCommand):
    help = (
        'Envía un recordatorio por email a las reservas confirmadas que empiezan '
        'dentro de RECORDATORIO_HORAS_ANTES horas (por defecto 3) y no lo hayan '
        'recibido todavía. Pensado para lanzarse periódicamente vía cron.'
    )

    def handle(self, *args, **options):
        horas_antes = int(os.environ.get('RECORDATORIO_HORAS_ANTES', 3))
        ahora = timezone.localtime()
        limite = ahora + timedelta(hours=horas_antes)

        candidatas = Reserva.objects.filter(
            estado=Reserva.ESTADO_CONFIRMADA,
            recordatorio_enviado=False,
            fecha__gte=ahora.date(),
            fecha__lte=limite.date(),
        ).select_related('usuario', 'pista', 'pista__urbanizacion')

        enviados = 0
        for reserva in candidatas:
            inicio_dt = timezone.make_aware(datetime.combine(reserva.fecha, reserva.hora_inicio))
            if ahora <= inicio_dt <= limite:
                enviar_recordatorio_reserva(reserva)
                reserva.recordatorio_enviado = True
                reserva.save(update_fields=['recordatorio_enviado'])
                enviados += 1

        self.stdout.write(self.style.SUCCESS(f'{enviados} recordatorio(s) enviado(s).'))
