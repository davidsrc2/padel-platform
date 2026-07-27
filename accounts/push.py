import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

from .models import PushSubscription

logger = logging.getLogger(__name__)


def enviar_push(usuario, titulo, cuerpo, url='/'):
    if not settings.VAPID_PRIVATE_KEY:
        return  # push no configurado (faltan las claves VAPID): no-op silencioso

    payload = json.dumps({'titulo': titulo, 'cuerpo': cuerpo, 'url': url})

    for sub in PushSubscription.objects.filter(usuario=usuario):
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={'sub': f'mailto:{settings.VAPID_CLAIM_EMAIL}'},
            )
        except WebPushException as e:
            status = getattr(e.response, 'status_code', None)
            if status in (404, 410):
                # La suscripción ya no existe en el navegador (desinstalada,
                # caducada...): la limpiamos en vez de seguir reintentando.
                sub.delete()
            else:
                logger.warning('Fallo enviando push a %s: %s', usuario.username, e)
