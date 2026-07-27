from django.core.exceptions import ValidationError
from django.test import TestCase

from pistas.models import Pista
from .models import Urbanizacion


class UrbanizacionNumPistasTest(TestCase):

    def test_no_deja_bajar_num_pistas_por_debajo_de_las_existentes(self):
        urb = Urbanizacion.objects.create(nombre='Test', direccion='x', num_pistas=2)
        Pista.objects.create(urbanizacion=urb, nombre='Pista 1')
        Pista.objects.create(urbanizacion=urb, nombre='Pista 2')

        urb.num_pistas = 1
        with self.assertRaises(ValidationError):
            urb.save()
