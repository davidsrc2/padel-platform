from django.urls import path

from accounts import views as accounts_views
from pistas import views as pistas_views
from urbanizaciones import views as urbanizaciones_views
from viviendas import views as viviendas_views

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.inicio, name='inicio'),

    path('urbanizacion/', urbanizaciones_views.panel_urbanizacion, name='urbanizacion'),
    path('urbanizacion/crear/', urbanizaciones_views.panel_urbanizacion_crear, name='urbanizacion_crear'),

    path('portales/', viviendas_views.panel_portales, name='portales'),
    path('portales/crear/', viviendas_views.panel_portal_crear, name='portal_crear'),
    path('portales/<int:pk>/eliminar/', viviendas_views.panel_portal_eliminar, name='portal_eliminar'),
    path('portales/<int:portal_pk>/viviendas/crear/', viviendas_views.panel_vivienda_crear, name='vivienda_crear'),
    path('viviendas/<int:pk>/eliminar/', viviendas_views.panel_vivienda_eliminar, name='vivienda_eliminar'),

    path('pistas/', pistas_views.panel_pistas, name='pistas'),
    path('pistas/crear/', pistas_views.panel_pista_crear, name='pista_crear'),
    path('pistas/<int:pk>/toggle/', pistas_views.panel_pista_toggle, name='pista_toggle'),
    path('pistas/<int:pk>/eliminar/', pistas_views.panel_pista_eliminar, name='pista_eliminar'),
    path('pistas/<int:pista_pk>/bloqueos/crear/', pistas_views.panel_bloqueo_crear, name='bloqueo_crear'),
    path('bloqueos/<int:pk>/eliminar/', pistas_views.panel_bloqueo_eliminar, name='bloqueo_eliminar'),

    path('usuarios/', accounts_views.panel_usuarios, name='usuarios'),
    path('usuarios/<int:pk>/aprobar/', accounts_views.panel_usuario_aprobar, name='usuario_aprobar'),
    path('usuarios/<int:pk>/rechazar/', accounts_views.panel_usuario_rechazar, name='usuario_rechazar'),

    path('estadisticas/', views.estadisticas, name='estadisticas'),
]
