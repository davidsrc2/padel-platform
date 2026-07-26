from django.core.management.base import BaseCommand

from accounts.models import Usuario
from pistas.models import Pista
from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal, Vivienda

PASSWORD = 'Test1234'


class Command(BaseCommand):
    help = 'Crea usuarios y datos de demo (superadmin, admin_urb, vecino) si no existen'

    def handle(self, *args, **options):
        urb, _ = Urbanizacion.objects.get_or_create(
            nombre='Urbanizacion Test',
            defaults={'direccion': 'Calle Falsa 1', 'num_pistas': 2},
        )
        portal, _ = Portal.objects.get_or_create(urbanizacion=urb, nombre='Portal A')
        vivienda, _ = Vivienda.objects.get_or_create(portal=portal, piso='1', puerta='A')
        Pista.objects.get_or_create(urbanizacion=urb, nombre='Pista 1', defaults={'activa': True})

        self._crear_usuario('superadmin', Usuario.ROL_SUPERADMIN, vivienda, superuser=True)
        self._crear_usuario('admin_urb', Usuario.ROL_ADMIN_URB, vivienda)
        self._crear_usuario('vecino', Usuario.ROL_VECINO, vivienda)

        self.stdout.write(self.style.SUCCESS('Usuarios de demo listos (superadmin / admin_urb / vecino, password Test1234)'))

    def _crear_usuario(self, username, rol, vivienda, superuser=False):
        usuario, creado = Usuario.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@test.com'},
        )
        if creado:
            usuario.set_password(PASSWORD)
        usuario.rol = rol
        usuario.vivienda = vivienda
        usuario.aprobado = True
        usuario.is_active = True
        if superuser:
            usuario.is_staff = True
            usuario.is_superuser = True
        usuario.save()
