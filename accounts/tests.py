from django.test import TestCase

from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal, Vivienda
from .models import Usuario


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
