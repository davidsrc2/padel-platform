import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from reservas.models import ResultadoPartido


class Command(BaseCommand):
    help = (
        'Confirma automáticamente los resultados pendientes que llevan más de '
        'AUTOCONFIRMAR_HORAS (por defecto 48) sin respuesta del equipo rival. '
        'Pensado para lanzarse periódicamente vía cron, igual que enviar_recordatorios.'
    )

    def handle(self, *args, **options):
        horas = int(os.environ.get('AUTOCONFIRMAR_HORAS', 48))
        limite = timezone.now() - timedelta(hours=horas)

        pendientes = ResultadoPartido.objects.filter(
            estado=ResultadoPartido.ESTADO_PENDIENTE,
            fecha_registro__lt=limite,
        )
        n = 0
        for resultado in pendientes:
            resultado.estado = ResultadoPartido.ESTADO_CONFIRMADO
            resultado.fecha_confirmacion = timezone.now()
            resultado.save()
            n += 1

        self.stdout.write(self.style.SUCCESS(f'{n} resultado(s) autoconfirmado(s).'))
