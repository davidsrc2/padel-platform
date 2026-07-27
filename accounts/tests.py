import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal, Vivienda
from .models import PushSubscription, Usuario
from .push import enviar_push


class RegistroTest(TestCase):

    def test_registro_crea_usuario_no_aprobado(self):
        urb = Urbanizacion.objects.create(nombre='Test', direccion='x')
        portal = Portal.objects.create(urbanizacion=urb, nombre='A')
        vivienda = Vivienda.objects.create(portal=portal, piso='1')

        resp = self.client.post('/accounts/registro/', {
            'username': 'nuevo_vecino',
            'first_name': 'Nuevo',
            'last_name': 'Vecino',
            'email': 'nuevo@example.com',
            'telefono': '',
            'urbanizacion': urb.pk,
            'portal': portal.pk,
            'vivienda': vivienda.pk,
            'password1': 'contraseña-larga-123',
            'password2': 'contraseña-larga-123',
        })
        self.assertEqual(resp.status_code, 302)
        usuario = Usuario.objects.get(username='nuevo_vecino')
        self.assertFalse(usuario.aprobado)
        self.assertEqual(usuario.rol, Usuario.ROL_VECINO)


class CrearComunidadTest(TestCase):

    def _datos_validos(self, **overrides):
        datos = {
            'urb_nombre': 'Residencial Las Palmeras',
            'urb_direccion': 'Av. de las Palmeras 10',
            'num_pistas': 3,
            'portal_nombre': 'A',
            'piso': 'Bajo',
            'puerta': 'B',
            'username': 'admin_palmeras',
            'first_name': 'Laura',
            'last_name': 'Gómez',
            'email': 'laura@example.com',
            'telefono': '',
            'password1': 'ClaveSegura123!',
            'password2': 'ClaveSegura123!',
        }
        datos.update(overrides)
        return datos

    def test_crea_urbanizacion_portal_vivienda_y_admin_aprobado(self):
        resp = self.client.post('/accounts/crear-comunidad/', self._datos_validos())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/panel/')

        urb = Urbanizacion.objects.get(nombre='Residencial Las Palmeras')
        self.assertEqual(urb.num_pistas, 3)

        admin = Usuario.objects.get(username='admin_palmeras')
        self.assertEqual(admin.rol, Usuario.ROL_ADMIN_URB)
        self.assertTrue(admin.aprobado)
        self.assertEqual(admin.urbanizacion, urb)

    def test_deja_logueado_tras_crear(self):
        self.client.post('/accounts/crear-comunidad/', self._datos_validos())
        resp = self.client.get('/panel/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Residencial Las Palmeras')

    def test_username_duplicado_no_crea_nada(self):
        Usuario.objects.create_user(username='admin_palmeras', password='x')
        resp = self.client.post('/accounts/crear-comunidad/', self._datos_validos())
        self.assertEqual(resp.status_code, 200)  # vuelve a mostrar el form con el error
        self.assertFalse(Urbanizacion.objects.filter(nombre='Residencial Las Palmeras').exists())

    def test_admin_de_una_comunidad_no_ve_datos_de_otra(self):
        self.client.post('/accounts/crear-comunidad/', self._datos_validos())
        self.client.logout()
        self.client.post('/accounts/crear-comunidad/', self._datos_validos(
            urb_nombre='Otra Urb', username='admin_otra', email='otra@example.com',
        ))
        resp = self.client.get('/panel/')
        self.assertContains(resp, 'Otra Urb')
        self.assertNotContains(resp, 'Residencial Las Palmeras')


class PerfilTest(TestCase):

    def test_perfil_requiere_login(self):
        resp = self.client.get('/accounts/perfil/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_perfil_muestra_los_datos_del_usuario_logueado(self):
        urb = Urbanizacion.objects.create(nombre='Test', direccion='x')
        portal = Portal.objects.create(urbanizacion=urb, nombre='A')
        vivienda = Vivienda.objects.create(portal=portal, piso='1')
        usuario = Usuario.objects.create_user(
            username='vecino1', password='pass', vivienda=vivienda, aprobado=True,
            email='vecino1@example.com',
        )
        self.client.force_login(usuario)
        resp = self.client.get('/accounts/perfil/')
        self.assertContains(resp, 'vecino1@example.com')

    def test_perfil_permite_editar_datos_propios(self):
        urb = Urbanizacion.objects.create(nombre='Test', direccion='x')
        portal = Portal.objects.create(urbanizacion=urb, nombre='A')
        vivienda = Vivienda.objects.create(portal=portal, piso='1')
        usuario = Usuario.objects.create_user(
            username='vecino1', password='pass', vivienda=vivienda, aprobado=True,
            email='viejo@example.com',
        )
        self.client.force_login(usuario)
        resp = self.client.post('/accounts/perfil/', {
            'first_name': 'Nuevo', 'last_name': 'Nombre',
            'email': 'nuevo@example.com', 'telefono': '600111222',
        })
        self.assertEqual(resp.status_code, 302)
        usuario.refresh_from_db()
        self.assertEqual(usuario.email, 'nuevo@example.com')
        self.assertEqual(usuario.telefono, '600111222')


def _crear_usuario_basico(username='vecino1'):
    urb = Urbanizacion.objects.create(nombre='Test', direccion='x')
    portal = Portal.objects.create(urbanizacion=urb, nombre='A')
    vivienda = Vivienda.objects.create(portal=portal, piso='1')
    return Usuario.objects.create_user(
        username=username, password='pass', vivienda=vivienda, aprobado=True,
        email=f'{username}@example.com',
    )


class PushSuscripcionVistasTest(TestCase):

    def test_suscribir_requiere_login(self):
        resp = self.client.post(
            '/accounts/push/suscribir/',
            data=json.dumps({'endpoint': 'https://x.test/y', 'keys': {'p256dh': 'a', 'auth': 'b'}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_suscribir_guarda_la_suscripcion(self):
        usuario = _crear_usuario_basico()
        self.client.force_login(usuario)
        resp = self.client.post(
            '/accounts/push/suscribir/',
            data=json.dumps({
                'endpoint': 'https://push.test/abc123',
                'keys': {'p256dh': 'clave-p256dh', 'auth': 'clave-auth'},
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        sub = PushSubscription.objects.get(endpoint='https://push.test/abc123')
        self.assertEqual(sub.usuario, usuario)
        self.assertEqual(sub.p256dh, 'clave-p256dh')

    def test_suscribir_sin_datos_completos_devuelve_400(self):
        usuario = _crear_usuario_basico()
        self.client.force_login(usuario)
        resp = self.client.post(
            '/accounts/push/suscribir/',
            data=json.dumps({'endpoint': 'https://push.test/abc123', 'keys': {}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PushSubscription.objects.exists())

    def test_desuscribir_borra_la_suscripcion(self):
        usuario = _crear_usuario_basico()
        sub = PushSubscription.objects.create(
            usuario=usuario, endpoint='https://push.test/abc123', p256dh='a', auth='b',
        )
        self.client.force_login(usuario)
        resp = self.client.post(
            '/accounts/push/desuscribir/',
            data=json.dumps({'endpoint': sub.endpoint}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PushSubscription.objects.filter(pk=sub.pk).exists())

    def test_no_se_puede_desuscribir_una_suscripcion_ajena_con_endpoint_de_otro(self):
        usuario1 = _crear_usuario_basico('vecino1')
        usuario2 = _crear_usuario_basico('vecino2')
        sub_ajena = PushSubscription.objects.create(
            usuario=usuario1, endpoint='https://push.test/de-otro', p256dh='a', auth='b',
        )
        self.client.force_login(usuario2)
        self.client.post(
            '/accounts/push/desuscribir/',
            data=json.dumps({'endpoint': sub_ajena.endpoint}),
            content_type='application/json',
        )
        self.assertTrue(PushSubscription.objects.filter(pk=sub_ajena.pk).exists())


class EnviarPushTest(TestCase):

    @override_settings(VAPID_PRIVATE_KEY='')
    def test_no_hace_nada_si_no_hay_claves_vapid_configuradas(self):
        usuario = _crear_usuario_basico()
        PushSubscription.objects.create(usuario=usuario, endpoint='https://x', p256dh='a', auth='b')
        with patch('accounts.push.webpush') as mock_webpush:
            enviar_push(usuario, 'Título', 'Cuerpo')
            mock_webpush.assert_not_called()

    @override_settings(VAPID_PRIVATE_KEY='clave-privada-de-prueba', VAPID_CLAIM_EMAIL='test@example.com')
    def test_llama_a_webpush_por_cada_suscripcion_activa(self):
        usuario = _crear_usuario_basico()
        PushSubscription.objects.create(usuario=usuario, endpoint='https://x/1', p256dh='a', auth='b')
        PushSubscription.objects.create(usuario=usuario, endpoint='https://x/2', p256dh='c', auth='d')
        with patch('accounts.push.webpush') as mock_webpush:
            enviar_push(usuario, 'Título', 'Cuerpo', url='/reservas/')
            self.assertEqual(mock_webpush.call_count, 2)

    @override_settings(VAPID_PRIVATE_KEY='clave-privada-de-prueba')
    def test_borra_la_suscripcion_si_el_navegador_ya_no_existe(self):
        from pywebpush import WebPushException

        usuario = _crear_usuario_basico()
        sub = PushSubscription.objects.create(usuario=usuario, endpoint='https://x/1', p256dh='a', auth='b')

        class RespuestaFalsa:
            status_code = 410

        with patch('accounts.push.webpush', side_effect=WebPushException('caducada', response=RespuestaFalsa())):
            enviar_push(usuario, 'Título', 'Cuerpo')

        self.assertFalse(PushSubscription.objects.filter(pk=sub.pk).exists())
