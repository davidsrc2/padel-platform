import os

from django.core.management.base import BaseCommand

from accounts.models import Usuario


class Command(BaseCommand):
    help = (
        'Crea o actualiza el superadmin a partir de las variables de entorno '
        'DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD. '
        'Idempotente: seguro de ejecutar en cada deploy.'
    )

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')

        if not username or not password:
            self.stdout.write(
                'DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD no definidas, se omite.'
            )
            return

        usuario, creado = Usuario.objects.get_or_create(username=username)
        if creado:
            usuario.set_password(password)
        if email:
            usuario.email = email
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.is_active = True
        usuario.rol = Usuario.ROL_SUPERADMIN
        usuario.aprobado = True
        usuario.save()

        self.stdout.write(self.style.SUCCESS(f'Superadmin "{username}" listo.'))
