import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _enviar(reserva, asunto, cuerpo):
    if not reserva.usuario.email:
        return
    try:
        send_mail(
            subject=f'[Pádel] {asunto}',
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reserva.usuario.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Fallo enviando email de reserva a %s', reserva.usuario.email)


def enviar_confirmacion_reserva(reserva):
    nombre = reserva.usuario.get_full_name() or reserva.usuario.username
    _enviar(
        reserva,
        asunto='Reserva confirmada',
        cuerpo=(
            f'Hola {nombre},\n\n'
            f'Tu reserva ha sido confirmada:\n'
            f'Pista: {reserva.pista.nombre}\n'
            f'Fecha: {reserva.fecha.strftime("%d/%m/%Y")}\n'
            f'Hora: {reserva.hora_inicio.strftime("%H:%M")}–{reserva.hora_fin.strftime("%H:%M")}\n'
            f'Urbanización: {reserva.urbanizacion.nombre}'
        ),
    )


def enviar_cancelacion_reserva(reserva):
    nombre = reserva.usuario.get_full_name() or reserva.usuario.username
    _enviar(
        reserva,
        asunto='Reserva cancelada',
        cuerpo=(
            f'Hola {nombre},\n\n'
            f'Tu reserva ha sido cancelada:\n'
            f'Pista: {reserva.pista.nombre}\n'
            f'Fecha: {reserva.fecha.strftime("%d/%m/%Y")}\n'
            f'Hora: {reserva.hora_inicio.strftime("%H:%M")}–{reserva.hora_fin.strftime("%H:%M")}'
        ),
    )
