from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Usuario
from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal, Vivienda
from .models import BloqueoPista, Pista


class PistaLimiteTest(TestCase):

    def test_no_deja_superar_num_pistas(self):
        urb = Urbanizacion.objects.create(nombre='Test', direccion='x', num_pistas=1)
        Pista.objects.create(urbanizacion=urb, nombre='Pista 1')
        with self.assertRaises(ValidationError):
            Pista.objects.create(urbanizacion=urb, nombre='Pista 2')

    def test_editar_una_pista_existente_no_cuenta_como_nueva(self):
        urb = Urbanizacion.objects.create(nombre='Test', direccion='x', num_pistas=1)
        pista = Pista.objects.create(urbanizacion=urb, nombre='Pista 1')
        pista.activa = False
        pista.save()  # no debe lanzar ValidationError por "límite superado"


class BloqueoPistaTest(TestCase):

    def test_no_deja_bloquear_una_franja_con_reserva_confirmada(self):
        from reservas.models import Reserva  # import diferido, mismo motivo que en el modelo

        urb = Urbanizacion.objects.create(nombre='Test', direccion='x', num_pistas=1)
        pista = Pista.objects.create(urbanizacion=urb, nombre='Pista 1')
        portal = Portal.objects.create(urbanizacion=urb, nombre='A')
        vivienda = Vivienda.objects.create(portal=portal, piso='1')
        usuario = Usuario.objects.create_user(username='u1', password='pass', vivienda=vivienda, aprobado=True)

        manana = timezone.localdate() + timedelta(days=1)
        Reserva.objects.create(pista=pista, usuario=usuario, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 30))

        bloqueo = BloqueoPista(pista=pista, fecha=manana, hora_inicio=time(10, 30), hora_fin=time(12, 0))
        with self.assertRaises(ValidationError):
            bloqueo.full_clean()
