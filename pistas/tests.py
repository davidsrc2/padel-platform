from django.core.exceptions import ValidationError
from django.test import TestCase

from urbanizaciones.models import Urbanizacion
from .models import Pista


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
