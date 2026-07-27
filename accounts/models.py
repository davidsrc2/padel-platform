from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    ROL_VECINO = 'vecino'
    ROL_ADMIN_URB = 'admin_urb'
    ROL_SUPERADMIN = 'superadmin'

    ROLES = [
        (ROL_VECINO, 'Vecino'),
        (ROL_ADMIN_URB, 'Administrador de urbanización'),
        (ROL_SUPERADMIN, 'Superadmin'),
    ]

    vivienda = models.ForeignKey(
        'viviendas.Vivienda',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
    )
    rol = models.CharField(max_length=20, choices=ROLES, default=ROL_VECINO)
    aprobado = models.BooleanField(default=False)
    telefono = models.CharField(max_length=20, blank=True)

    @property
    def urbanizacion(self):
        return self.vivienda.portal.urbanizacion if self.vivienda else None

    def es_admin_de(self, urbanizacion):
        return self.rol in (self.ROL_ADMIN_URB, self.ROL_SUPERADMIN) and (
            self.rol == self.ROL_SUPERADMIN or self.urbanizacion == urbanizacion
        )

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_rol_display()})'


class PushSubscription(models.Model):
    """Una suscripción de notificaciones push por navegador/dispositivo."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    creada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Suscripción push de {self.usuario}'
