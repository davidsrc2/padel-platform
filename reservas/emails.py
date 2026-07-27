import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from accounts.push import enviar_push

logger = logging.getLogger(__name__)


def _enviar(reserva, asunto, estado_label, color, intro):
    nombre = reserva.usuario.get_full_name() or reserva.usuario.username

    enviar_push(
        reserva.usuario,
        titulo=f'Pádel · {asunto}',
        cuerpo=(
            f'{reserva.pista.nombre} · {reserva.fecha.strftime("%d/%m")} '
            f'{reserva.hora_inicio.strftime("%H:%M")}–{reserva.hora_fin.strftime("%H:%M")}'
        ),
        url='/reservas/mis-reservas/',
    )

    if not reserva.usuario.email:
        logger.warning(
            'No se envía email de reserva: el usuario "%s" no tiene email.',
            reserva.usuario.username,
        )
        return
    contexto = {
        'asunto': asunto,
        'estado_label': estado_label,
        'color': color,
        'intro': intro,
        'nombre': nombre,
        'pista': reserva.pista.nombre,
        'fecha': reserva.fecha.strftime('%d/%m/%Y'),
        'hora_inicio': reserva.hora_inicio.strftime('%H:%M'),
        'hora_fin': reserva.hora_fin.strftime('%H:%M'),
        'urbanizacion': reserva.urbanizacion.nombre,
    }
    html = render_to_string('emails/reserva.html', contexto)
    texto = (
        f'Hola {nombre},\n\n{intro}\n\n'
        f'Pista: {contexto["pista"]}\n'
        f'Fecha: {contexto["fecha"]}\n'
        f'Hora: {contexto["hora_inicio"]}–{contexto["hora_fin"]}\n'
        f'Urbanización: {contexto["urbanizacion"]}'
    )

    try:
        email = EmailMultiAlternatives(
            subject=f'[Pádel] {asunto}',
            body=texto,
            from_email=f'Pádel <{settings.DEFAULT_FROM_EMAIL}>',
            to=[reserva.usuario.email],
        )
        email.attach_alternative(html, 'text/html')
        email.send(fail_silently=False)
        logger.info('Email "%s" enviado a %s', asunto, reserva.usuario.email)
    except Exception:
        logger.exception('Fallo enviando email de reserva a %s', reserva.usuario.email)


def enviar_confirmacion_reserva(reserva):
    _enviar(
        reserva,
        asunto='Reserva confirmada',
        estado_label='Confirmada',
        color='#10b981',
        intro='Tu reserva ha sido confirmada. Aquí tienes los detalles:',
    )


def enviar_cancelacion_reserva(reserva):
    _enviar(
        reserva,
        asunto='Reserva cancelada',
        estado_label='Cancelada',
        color='#ef4444',
        intro='Tu reserva ha sido cancelada. Estos eran sus detalles:',
    )


def enviar_recordatorio_reserva(reserva):
    _enviar(
        reserva,
        asunto='Recordatorio de tu reserva',
        estado_label='Próximamente',
        color='#06b6d4',
        intro='Tu reserva es pronto. Aquí tienes los detalles:',
    )
