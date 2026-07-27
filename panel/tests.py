from django.test import TestCase
from django.urls import reverse

from accounts.models import Usuario
from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal, Vivienda


def _crear_urbanizacion_con_admin(nombre_urb, username_admin):
    urb = Urbanizacion.objects.create(nombre=nombre_urb, direccion='x')
    portal = Portal.objects.create(urbanizacion=urb, nombre='A')
    vivienda = Vivienda.objects.create(portal=portal, piso='1')
    admin = Usuario.objects.create_user(
        username=username_admin, password='pass', vivienda=vivienda,
        rol=Usuario.ROL_ADMIN_URB, aprobado=True,
    )
    return urb, portal, vivienda, admin


class PanelPermisosTest(TestCase):

    def test_vecino_no_puede_entrar_al_panel(self):
        urb, portal, vivienda, _ = _crear_urbanizacion_con_admin('Urb', 'admin1')
        vecino = Usuario.objects.create_user(
            username='vecino', password='pass', vivienda=vivienda,
            rol=Usuario.ROL_VECINO, aprobado=True,
        )
        self.client.force_login(vecino)
        resp = self.client.get(reverse('panel:inicio'))
        self.assertRedirects(resp, reverse('reservas:calendario'))

    def test_admin_urb_puede_entrar_al_panel(self):
        urb, portal, vivienda, admin = _crear_urbanizacion_con_admin('Urb', 'admin1')
        self.client.force_login(admin)
        resp = self.client.get(reverse('panel:inicio'))
        self.assertEqual(resp.status_code, 200)


class PanelMultiTenanciaTest(TestCase):
    """Un admin_urb no debe poder ver ni tocar datos de OTRA urbanización."""

    def test_admin_urb_no_puede_eliminar_portal_de_otra_urbanizacion(self):
        urb_a, portal_a, _, admin_a = _crear_urbanizacion_con_admin('Urb A', 'admin_a')
        urb_b, portal_b, _, _ = _crear_urbanizacion_con_admin('Urb B', 'admin_b')

        self.client.force_login(admin_a)
        resp = self.client.post(
            reverse('panel:portal_eliminar', args=[portal_b.pk]) + f'?urbanizacion={urb_b.pk}'
        )
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Portal.objects.filter(pk=portal_b.pk).exists())
