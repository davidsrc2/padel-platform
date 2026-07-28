from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Usuario
from pistas.models import Pista
from reservas.models import Participante, Reserva, ResultadoPartido, SetResultado
from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal, Vivienda

from .models import Seguimiento


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


def _reserva_pasada(pista, usuario, dias_atras=1):
    manana = timezone.localdate() + timedelta(days=1)
    r = Reserva.objects.create(
        pista=pista, usuario=usuario, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 30)
    )
    Reserva.objects.filter(pk=r.pk).update(fecha=timezone.localdate() - timedelta(days=dias_atras))
    r.refresh_from_db()
    return r


def _resultado_confirmado(reserva, ganador, perdedor):
    resultado = ResultadoPartido.objects.create(reserva=reserva, creado_por=ganador)
    Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_A, usuario=ganador)
    Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_B, usuario=perdedor)
    SetResultado.objects.create(resultado=resultado, numero=1, juegos_equipo_a=6, juegos_equipo_b=4)
    SetResultado.objects.create(resultado=resultado, numero=2, juegos_equipo_a=6, juegos_equipo_b=3)
    resultado.estado = ResultadoPartido.ESTADO_CONFIRMADO
    resultado.confirmado_por = perdedor
    resultado.fecha_confirmacion = timezone.now()
    resultado.save()
    return resultado


class SeguimientoModelTest(TestCase):

    def test_no_te_puedes_seguir_a_ti_mismo(self):
        urb, pista, user1, user2 = _setup()
        with self.assertRaises(ValidationError):
            Seguimiento.objects.create(seguidor=user1, seguido=user1)

    def test_no_se_puede_seguir_a_alguien_de_otra_urbanizacion(self):
        urb_a, pista_a, user_a, _ = _setup()
        urb_b = Urbanizacion.objects.create(nombre='Urb B', direccion='x')
        portal_b = Portal.objects.create(urbanizacion=urb_b, nombre='A')
        vivienda_b = Vivienda.objects.create(portal=portal_b, piso='1A')
        user_b = Usuario.objects.create_user(username='b1', password='pass', vivienda=vivienda_b, aprobado=True)

        with self.assertRaises(ValidationError):
            Seguimiento.objects.create(seguidor=user_a, seguido=user_b)

    def test_no_se_puede_duplicar_seguimiento(self):
        urb, pista, user1, user2 = _setup()
        Seguimiento.objects.create(seguidor=user1, seguido=user2)
        with self.assertRaises(ValidationError):
            Seguimiento.objects.create(seguidor=user1, seguido=user2)


class DirectorioVistaTest(TestCase):

    def test_requiere_login(self):
        resp = self.client.get('/social/vecinos/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_solo_muestra_vecinos_de_la_misma_urbanizacion(self):
        urb_a, pista_a, user_a, _ = _setup()
        urb_b = Urbanizacion.objects.create(nombre='Urb B', direccion='x')
        portal_b = Portal.objects.create(urbanizacion=urb_b, nombre='A')
        vivienda_b = Vivienda.objects.create(portal=portal_b, piso='1A')
        Usuario.objects.create_user(username='forastero', password='pass', vivienda=vivienda_b, aprobado=True)

        self.client.force_login(user_a)
        resp = self.client.get('/social/vecinos/')
        self.assertContains(resp, 'u2')
        self.assertNotContains(resp, 'forastero')

    def test_seguir_y_dejar_de_seguir(self):
        urb, pista, user1, user2 = _setup()
        self.client.force_login(user1)

        resp = self.client.post(f'/social/vecinos/{user2.pk}/seguir/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Seguimiento.objects.filter(seguidor=user1, seguido=user2).exists())

        resp = self.client.post(f'/social/vecinos/{user2.pk}/dejar-de-seguir/')
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Seguimiento.objects.filter(seguidor=user1, seguido=user2).exists())

    def test_no_te_puedes_seguir_a_ti_mismo_desde_la_vista(self):
        urb, pista, user1, user2 = _setup()
        self.client.force_login(user1)
        self.client.post(f'/social/vecinos/{user1.pk}/seguir/')
        self.assertFalse(Seguimiento.objects.filter(seguidor=user1, seguido=user1).exists())

    def test_no_se_puede_seguir_a_alguien_de_otra_urbanizacion_desde_la_vista(self):
        urb_a, pista_a, user_a, _ = _setup()
        urb_b = Urbanizacion.objects.create(nombre='Urb B', direccion='x')
        portal_b = Portal.objects.create(urbanizacion=urb_b, nombre='A')
        vivienda_b = Vivienda.objects.create(portal=portal_b, piso='1A')
        user_b = Usuario.objects.create_user(username='b1', password='pass', vivienda=vivienda_b, aprobado=True)

        self.client.force_login(user_a)
        self.client.post(f'/social/vecinos/{user_b.pk}/seguir/')
        self.assertFalse(Seguimiento.objects.filter(seguidor=user_a, seguido=user_b).exists())


class FeedVistaTest(TestCase):

    def test_requiere_login(self):
        resp = self.client.get('/social/feed/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_feed_solo_muestra_resultados_de_gente_que_sigo(self):
        urb, pista, user1, user2 = _setup()
        portal = Portal.objects.get(urbanizacion=urb)
        vivienda3 = Vivienda.objects.create(portal=portal, piso='3C')
        user3 = Usuario.objects.create_user(username='u3', password='pass', vivienda=vivienda3, aprobado=True)

        # user1 sigue a user2, pero no a user3
        Seguimiento.objects.create(seguidor=user1, seguido=user2)

        r_seguido = _reserva_pasada(pista, user2, dias_atras=1)
        _resultado_confirmado(r_seguido, ganador=user2, perdedor=user1)

        r_no_seguido = _reserva_pasada(pista, user3, dias_atras=2)
        _resultado_confirmado(r_no_seguido, ganador=user3, perdedor=user1)

        self.client.force_login(user1)
        resp = self.client.get('/social/feed/')
        self.assertContains(resp, 'u2')
        self.assertNotContains(resp, 'u3')

    def test_feed_no_muestra_resultados_pendientes(self):
        urb, pista, user1, user2 = _setup()
        Seguimiento.objects.create(seguidor=user1, seguido=user2)

        reserva = _reserva_pasada(pista, user2, dias_atras=1)
        resultado = ResultadoPartido.objects.create(reserva=reserva, creado_por=user2)
        Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_A, usuario=user2)
        Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_B, usuario=user1)
        SetResultado.objects.create(resultado=resultado, numero=1, juegos_equipo_a=6, juegos_equipo_b=4)
        SetResultado.objects.create(resultado=resultado, numero=2, juegos_equipo_a=6, juegos_equipo_b=3)
        # se queda "pendiente" (sin confirmar)

        self.client.force_login(user1)
        resp = self.client.get('/social/feed/')
        self.assertEqual(len(resp.context['resultados']), 0)
