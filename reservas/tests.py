from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, time, timedelta

from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal, Vivienda
from pistas.models import BloqueoPista, Pista
from accounts.models import Usuario
from .models import Reserva


def _setup():
    urb = Urbanizacion.objects.create(
        nombre='Test URB', direccion='Calle Test 1',
        hora_apertura=time(8, 0), hora_cierre=time(22, 0),
        duracion_franja_minutos=90, max_reservas_por_vivienda=1,
        antelacion_maxima_dias=7, cancelacion_minima_horas=2,
    )
    portal = Portal.objects.create(urbanizacion=urb, nombre='A')
    vivienda1 = Vivienda.objects.create(portal=portal, piso='1A')
    vivienda2 = Vivienda.objects.create(portal=portal, piso='2B')
    pista = Pista.objects.create(urbanizacion=urb, nombre='Pista 1')
    user1 = Usuario.objects.create_user(username='u1', password='pass', vivienda=vivienda1, aprobado=True)
    user2 = Usuario.objects.create_user(username='u2', password='pass', vivienda=vivienda2, aprobado=True)
    return urb, pista, user1, user2


class ReservaValidacionTest(TestCase):

    def test_reserva_correcta(self):
        urb, pista, user1, _ = _setup()
        manana = timezone.localdate() + timedelta(days=1)
        r = Reserva(pista=pista, usuario=user1, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 30))
        r.full_clean()  # no debe lanzar

    def test_solapamiento(self):
        urb, pista, user1, user2 = _setup()
        manana = timezone.localdate() + timedelta(days=1)
        Reserva.objects.create(pista=pista, usuario=user1, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 30))
        r2 = Reserva(pista=pista, usuario=user2, fecha=manana, hora_inicio=time(10, 30), hora_fin=time(12, 0))
        with self.assertRaises(ValidationError):
            r2.full_clean()

    def test_limite_reservas_por_vivienda(self):
        urb, pista, user1, _ = _setup()
        manana = timezone.localdate() + timedelta(days=1)
        Reserva.objects.create(pista=pista, usuario=user1, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 30))
        # Segunda reserva de la misma vivienda debe fallar
        r2 = Reserva(pista=pista, usuario=user1, fecha=manana, hora_inicio=time(12, 0), hora_fin=time(13, 30))
        with self.assertRaises(ValidationError):
            r2.full_clean()

    def test_fecha_pasada(self):
        urb, pista, user1, _ = _setup()
        ayer = timezone.localdate() - timedelta(days=1)
        r = Reserva(pista=pista, usuario=user1, fecha=ayer, hora_inicio=time(10, 0), hora_fin=time(11, 30))
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_antelacion_maxima(self):
        urb, pista, user1, _ = _setup()
        muy_lejos = timezone.localdate() + timedelta(days=30)
        r = Reserva(pista=pista, usuario=user1, fecha=muy_lejos, hora_inicio=time(10, 0), hora_fin=time(11, 30))
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_no_se_puede_reservar_franja_bloqueada_por_mantenimiento(self):
        urb, pista, user1, _ = _setup()
        manana = timezone.localdate() + timedelta(days=1)
        BloqueoPista.objects.create(pista=pista, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 0))
        r = Reserva(pista=pista, usuario=user1, fecha=manana, hora_inicio=time(10, 30), hora_fin=time(12, 0))
        with self.assertRaises(ValidationError):
            r.full_clean()


class ReservaVistasSeguridadTest(TestCase):

    def test_calendario_requiere_login(self):
        resp = self.client.get('/reservas/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_mis_reservas_requiere_login(self):
        resp = self.client.get('/reservas/mis-reservas/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_no_se_puede_reservar_pista_de_otra_urbanizacion(self):
        urb_a, pista_a, user_a, _ = _setup()
        urb_b = Urbanizacion.objects.create(nombre='Urb B', direccion='x')
        pista_b = Pista.objects.create(urbanizacion=urb_b, nombre='Pista 1')

        self.client.force_login(user_a)
        manana = timezone.localdate() + timedelta(days=1)
        resp = self.client.post('/reservas/reservar/', {
            'pista': pista_b.pk, 'fecha': str(manana), 'hora_inicio': '10:00:00',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Reserva.objects.filter(pista=pista_b, usuario=user_a).exists())

    def test_no_se_puede_cancelar_reserva_ajena(self):
        urb, pista, user1, user2 = _setup()
        manana = timezone.localdate() + timedelta(days=1)
        reserva = Reserva.objects.create(
            pista=pista, usuario=user1, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 30)
        )
        self.client.force_login(user2)
        resp = self.client.post(f'/reservas/cancelar/{reserva.pk}/')
        self.assertEqual(resp.status_code, 404)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.ESTADO_CONFIRMADA)

    def test_calendario_de_un_vecino_solo_muestra_pistas_de_su_urbanizacion(self):
        urb_a, pista_a, user_a, _ = _setup()
        urb_b = Urbanizacion.objects.create(nombre='Urb B', direccion='x')
        Pista.objects.create(urbanizacion=urb_b, nombre='Pista de otra urb')

        self.client.force_login(user_a)
        resp = self.client.get('/reservas/')
        self.assertContains(resp, pista_a.nombre)
        self.assertNotContains(resp, 'Pista de otra urb')
