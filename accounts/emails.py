import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def enviar_aprobacion_usuario(usuario):
    if not usuario.email:
        logger.warning(
            'No se envía email de aprobación: el usuario "%s" no tiene email.',
            usuario.username,
        )
        return

    nombre = usuario.get_full_name() or usuario.username
    login_url = f'{settings.SITE_URL}{reverse("accounts:login")}'
    contexto = {'nombre': nombre, 'login_url': login_url}
    html = render_to_string('emails/cuenta_aprobada.html', contexto)
    texto = (
        f'Hola {nombre},\n\n'
        f'Tu cuenta ha sido aprobada. Ya puedes acceder y reservar pista:\n'
        f'{login_url}'
    )

    try:
        email = EmailMultiAlternatives(
            subject='[Pádel] Tu cuenta ha sido aprobada',
            body=texto,
            from_email=f'Pádel <{settings.DEFAULT_FROM_EMAIL}>',
            to=[usuario.email],
        )
        email.attach_alternative(html, 'text/html')
        email.send(fail_silently=False)
        logger.info('Email de aprobación enviado a %s', usuario.email)
    except Exception:
        logger.exception('Fallo enviando email de aprobación a %s', usuario.email)
