from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, time, timedelta

from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal, Vivienda
from pistas.models import BloqueoPista, Pista
from accounts.models import Usuario
from .estadisticas import calcular_estadisticas
from .forms import ResultadoPartidoForm
from .models import Participante, Reserva, ResultadoPartido, SetResultado, validar_set


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


def _setup_4_jugadores():
    urb, pista, user1, user2 = _setup()
    portal = Portal.objects.get(urbanizacion=urb)
    vivienda3 = Vivienda.objects.create(portal=portal, piso='3C')
    vivienda4 = Vivienda.objects.create(portal=portal, piso='4D')
    user3 = Usuario.objects.create_user(username='u3', password='pass', vivienda=vivienda3, aprobado=True)
    user4 = Usuario.objects.create_user(username='u4', password='pass', vivienda=vivienda4, aprobado=True)
    return urb, pista, user1, user2, user3, user4


def _reserva_pasada(pista, usuario, dias_atras=1, hora_inicio=time(10, 0), hora_fin=time(11, 30)):
    """Crea una reserva válida (para mañana) y la retrasa saltándose full_clean(),
    ya que Reserva.save() no deja crear una reserva directamente en el pasado."""
    manana = timezone.localdate() + timedelta(days=1)
    r = Reserva.objects.create(pista=pista, usuario=usuario, fecha=manana, hora_inicio=hora_inicio, hora_fin=hora_fin)
    Reserva.objects.filter(pk=r.pk).update(fecha=timezone.localdate() - timedelta(days=dias_atras))
    r.refresh_from_db()
    return r


def _resultado_2_0(reserva, creador, companero, rival1, rival2=None, rival1_invitado=None):
    """Crea un resultado 6-4, 6-3 (equipo A gana 2-0), pendiente de confirmar.
    rival1_invitado (nombre) sustituye a rival1 (Usuario) si se indica."""
    resultado = ResultadoPartido.objects.create(reserva=reserva, creado_por=creador)
    Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_A, usuario=creador)
    if companero:
        Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_A, usuario=companero)
    if rival1_invitado:
        Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_B, nombre_invitado=rival1_invitado)
    else:
        Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_B, usuario=rival1)
    if rival2:
        Participante.objects.create(resultado=resultado, equipo=Participante.EQUIPO_B, usuario=rival2)
    SetResultado.objects.create(resultado=resultado, numero=1, juegos_equipo_a=6, juegos_equipo_b=4)
    SetResultado.objects.create(resultado=resultado, numero=2, juegos_equipo_a=6, juegos_equipo_b=3)
    return resultado


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


class ValidarSetTest(TestCase):

    def test_sets_validos(self):
        for a, b in [(6, 4), (6, 0), (7, 5), (7, 6)]:
            validar_set(a, b)  # no debe lanzar

    def test_sets_invalidos(self):
        for a, b in [(6, 5), (8, 6), (6, 6), (5, 4)]:
            with self.assertRaises(ValidationError):
                validar_set(a, b)

    def test_super_tiebreak_valido(self):
        validar_set(10, 8, es_super_tiebreak=True)
        validar_set(11, 9, es_super_tiebreak=True)

    def test_super_tiebreak_invalido(self):
        with self.assertRaises(ValidationError):
            validar_set(10, 9, es_super_tiebreak=True)


class ResultadoPartidoModelTest(TestCase):

    def test_no_se_puede_registrar_resultado_de_reserva_no_terminada(self):
        urb, pista, user1, user2 = _setup()
        manana = timezone.localdate() + timedelta(days=1)
        reserva = Reserva.objects.create(
            pista=pista, usuario=user1, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 30)
        )
        resultado = ResultadoPartido(reserva=reserva, creado_por=user1)
        with self.assertRaises(ValidationError):
            resultado.full_clean()

    def test_no_se_puede_registrar_resultado_de_reserva_no_confirmada(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        Reserva.objects.filter(pk=reserva.pk).update(estado=Reserva.ESTADO_CANCELADA)
        reserva.refresh_from_db()
        resultado = ResultadoPartido(reserva=reserva, creado_por=user1)
        with self.assertRaises(ValidationError):
            resultado.full_clean()

    def test_ganador_y_gano_segun_sets(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        resultado = _resultado_2_0(reserva, user1, None, user2)
        self.assertEqual(resultado.ganador, 'A')
        self.assertTrue(resultado.gano(user1))
        self.assertFalse(resultado.gano(user2))


class ResultadoPartidoFormTest(TestCase):

    def _form(self, usuario, reserva, data):
        return ResultadoPartidoForm(data, usuario=usuario, reserva=reserva)

    def test_resultado_valido_2_0(self):
        urb, pista, user1, user2, user3, user4 = _setup_4_jugadores()
        reserva = _reserva_pasada(pista, user1)
        form = self._form(user1, reserva, {
            'equipo_b_jugador1': user2.pk,
            'set1_a': 6, 'set1_b': 4, 'set2_a': 6, 'set2_b': 3,
        })
        self.assertTrue(form.is_valid(), form.errors)
        resultado = form.save()
        self.assertEqual(resultado.ganador, 'A')

    def test_resultado_valido_2_1_con_super_tiebreak(self):
        urb, pista, user1, user2, user3, user4 = _setup_4_jugadores()
        reserva = _reserva_pasada(pista, user1)
        form = self._form(user1, reserva, {
            'equipo_a_companero': user3.pk,
            'equipo_b_jugador1': user2.pk, 'equipo_b_jugador2': user4.pk,
            'set1_a': 6, 'set1_b': 4,
            'set2_a': 3, 'set2_b': 6,
            'set3_a': 10, 'set3_b': 8, 'set3_es_super_tiebreak': True,
        })
        self.assertTrue(form.is_valid(), form.errors)
        resultado = form.save()
        self.assertEqual(resultado.ganador, 'A')
        self.assertEqual(resultado.jugadores(Participante.EQUIPO_A).count(), 2)
        self.assertEqual(resultado.jugadores(Participante.EQUIPO_B).count(), 2)

    def test_un_set_cada_uno_sin_tercero_da_error(self):
        urb, pista, user1, user2, user3, user4 = _setup_4_jugadores()
        reserva = _reserva_pasada(pista, user1)
        form = self._form(user1, reserva, {
            'equipo_b_jugador1': user2.pk,
            'set1_a': 6, 'set1_b': 4, 'set2_a': 3, 'set2_b': 6,
        })
        self.assertFalse(form.is_valid())

    def test_marcador_invalido_da_error(self):
        urb, pista, user1, user2, user3, user4 = _setup_4_jugadores()
        reserva = _reserva_pasada(pista, user1)
        form = self._form(user1, reserva, {
            'equipo_b_jugador1': user2.pk,
            'set1_a': 6, 'set1_b': 5, 'set2_a': 6, 'set2_b': 3,
        })
        self.assertFalse(form.is_valid())

    def test_jugador_repetido_en_dos_equipos_da_error(self):
        urb, pista, user1, user2, user3, user4 = _setup_4_jugadores()
        reserva = _reserva_pasada(pista, user1)
        form = self._form(user1, reserva, {
            'equipo_b_jugador1': user1.pk,
            'set1_a': 6, 'set1_b': 4, 'set2_a': 6, 'set2_b': 3,
        })
        self.assertFalse(form.is_valid())

    def test_rival_invitado_sin_perfil(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        form = self._form(user1, reserva, {
            'equipo_b_jugador1_invitado': 'Pepe de fuera',
            'set1_a': 6, 'set1_b': 4, 'set2_a': 6, 'set2_b': 3,
        })
        self.assertTrue(form.is_valid(), form.errors)
        resultado = form.save()
        rivales = list(resultado.jugadores(Participante.EQUIPO_B))
        self.assertEqual(len(rivales), 1)
        self.assertIsNone(rivales[0].usuario)
        self.assertEqual(rivales[0].nombre, 'Pepe de fuera')

    def test_mezcla_perfil_y_nombre_en_mismo_hueco_da_error(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        form = self._form(user1, reserva, {
            'equipo_b_jugador1': user2.pk,
            'equipo_b_jugador1_invitado': 'Pepe de fuera',
            'set1_a': 6, 'set1_b': 4, 'set2_a': 6, 'set2_b': 3,
        })
        self.assertFalse(form.is_valid())

    def test_falta_rival_obligatorio_da_error(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        form = self._form(user1, reserva, {
            'set1_a': 6, 'set1_b': 4, 'set2_a': 6, 'set2_b': 3,
        })
        self.assertFalse(form.is_valid())


class CrearResultadoVistaTest(TestCase):

    def test_no_se_puede_registrar_resultado_de_reserva_futura(self):
        urb, pista, user1, user2 = _setup()
        manana = timezone.localdate() + timedelta(days=1)
        reserva = Reserva.objects.create(
            pista=pista, usuario=user1, fecha=manana, hora_inicio=time(10, 0), hora_fin=time(11, 30)
        )
        self.client.force_login(user1)
        resp = self.client.post(f'/reservas/partidos/{reserva.pk}/registrar/', {
            'equipo_b_jugador1': user2.pk, 'set1_a': 6, 'set1_b': 4, 'set2_a': 6, 'set2_b': 3,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ResultadoPartido.objects.filter(reserva=reserva).exists())

    def test_no_se_puede_duplicar_resultado(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        _resultado_2_0(reserva, user1, None, user2)
        self.client.force_login(user1)
        resp = self.client.get(f'/reservas/partidos/{reserva.pk}/registrar/')
        self.assertEqual(resp.status_code, 302)

    def test_otro_usuario_no_puede_registrar_resultado_de_reserva_ajena(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        self.client.force_login(user2)
        resp = self.client.get(f'/reservas/partidos/{reserva.pk}/registrar/')
        self.assertEqual(resp.status_code, 404)


class ConfirmarDisputarResultadoTest(TestCase):

    def test_solo_rival_puede_confirmar(self):
        urb, pista, user1, user2, user3, _ = _setup_4_jugadores()
        reserva = _reserva_pasada(pista, user1)
        resultado = _resultado_2_0(reserva, user1, None, user2)

        self.client.force_login(user3)
        resp = self.client.post(f'/reservas/partidos/{resultado.pk}/confirmar/')
        resultado.refresh_from_db()
        self.assertEqual(resultado.estado, ResultadoPartido.ESTADO_PENDIENTE)

    def test_creador_no_puede_confirmar_su_propio_resultado(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        resultado = _resultado_2_0(reserva, user1, None, user2)

        self.client.force_login(user1)
        resp = self.client.post(f'/reservas/partidos/{resultado.pk}/confirmar/')
        resultado.refresh_from_db()
        self.assertEqual(resultado.estado, ResultadoPartido.ESTADO_PENDIENTE)

    def test_rival_puede_confirmar(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        resultado = _resultado_2_0(reserva, user1, None, user2)

        self.client.force_login(user2)
        resp = self.client.post(f'/reservas/partidos/{resultado.pk}/confirmar/')
        resultado.refresh_from_db()
        self.assertEqual(resultado.estado, ResultadoPartido.ESTADO_CONFIRMADO)
        self.assertEqual(resultado.confirmado_por, user2)

    def test_rival_puede_disputar(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        resultado = _resultado_2_0(reserva, user1, None, user2)

        self.client.force_login(user2)
        resp = self.client.post(f'/reservas/partidos/{resultado.pk}/disputar/')
        resultado.refresh_from_db()
        self.assertEqual(resultado.estado, ResultadoPartido.ESTADO_DISPUTADO)


class PanelResolverResultadoTest(TestCase):

    def test_admin_urb_no_puede_resolver_resultado_de_otra_urbanizacion(self):
        urb_a, pista_a, user1_a, user2_a = _setup()
        portal_a = Portal.objects.get(urbanizacion=urb_a)
        vivienda_admin_a = Vivienda.objects.create(portal=portal_a, piso='9Z')
        admin_a = Usuario.objects.create_user(
            username='admin_a', password='pass', vivienda=vivienda_admin_a,
            rol=Usuario.ROL_ADMIN_URB, aprobado=True,
        )

        urb_b = Urbanizacion.objects.create(nombre='Urb B', direccion='x')
        portal_b = Portal.objects.create(urbanizacion=urb_b, nombre='A')
        vivienda_b1 = Vivienda.objects.create(portal=portal_b, piso='1A')
        vivienda_b2 = Vivienda.objects.create(portal=portal_b, piso='2B')
        pista_b = Pista.objects.create(urbanizacion=urb_b, nombre='Pista 1')
        user1_b = Usuario.objects.create_user(username='b1', password='pass', vivienda=vivienda_b1, aprobado=True)
        user2_b = Usuario.objects.create_user(username='b2', password='pass', vivienda=vivienda_b2, aprobado=True)

        reserva_b = _reserva_pasada(pista_b, user1_b)
        resultado_b = _resultado_2_0(reserva_b, user1_b, None, user2_b)
        Reserva.objects.filter(pk=reserva_b.pk).update(estado=Reserva.ESTADO_CONFIRMADA)
        resultado_b.estado = ResultadoPartido.ESTADO_DISPUTADO
        resultado_b.save()

        self.client.force_login(admin_a)
        resp = self.client.post(f'/panel/resultados/{resultado_b.pk}/resolver/', {'accion': 'confirmar'})
        self.assertEqual(resp.status_code, 404)
        resultado_b.refresh_from_db()
        self.assertEqual(resultado_b.estado, ResultadoPartido.ESTADO_DISPUTADO)


class EstadisticasTest(TestCase):

    def test_calculo_basico_de_victorias_derrotas_y_racha(self):
        urb, pista, user1, user2 = _setup()

        r1 = _reserva_pasada(pista, user1, dias_atras=3, hora_inicio=time(9, 0), hora_fin=time(10, 30))
        res1 = _resultado_2_0(r1, user1, None, user2)  # user1 gana
        res1.estado = ResultadoPartido.ESTADO_CONFIRMADO
        res1.save()

        r2 = _reserva_pasada(pista, user1, dias_atras=2, hora_inicio=time(9, 0), hora_fin=time(10, 30))
        res2 = _resultado_2_0(r2, user2, None, user1)  # user2 gana (user1 en equipo_b, pierde)
        res2.estado = ResultadoPartido.ESTADO_CONFIRMADO
        res2.save()

        r3 = _reserva_pasada(pista, user1, dias_atras=1, hora_inicio=time(9, 0), hora_fin=time(10, 30))
        res3 = _resultado_2_0(r3, user1, None, user2)  # user1 gana otra vez
        res3.estado = ResultadoPartido.ESTADO_CONFIRMADO
        res3.save()

        stats = calcular_estadisticas(user1)
        self.assertEqual(stats['jugados'], 3)
        self.assertEqual(stats['ganados'], 2)
        self.assertEqual(stats['perdidos'], 1)
        self.assertEqual(stats['racha_actual'], 1)
        self.assertEqual(stats['ultimos_resultados'], ['V', 'D', 'V'])

    def test_no_cuenta_resultados_pendientes_ni_disputados(self):
        urb, pista, user1, user2 = _setup()
        reserva = _reserva_pasada(pista, user1)
        _resultado_2_0(reserva, user1, None, user2)  # se queda pendiente

        stats = calcular_estadisticas(user1)
        self.assertEqual(stats['jugados'], 0)
