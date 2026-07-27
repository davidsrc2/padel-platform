from django.urls import path
from . import views

app_name = 'reservas'

urlpatterns = [
    path('', views.calendario, name='calendario'),
    path('reservar/', views.crear_reserva, name='crear'),
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('cancelar/<int:pk>/', views.cancelar_reserva, name='cancelar'),
    path('companeros/<int:pk>/', views.editar_companeros, name='editar_companeros'),

    path('partidos/', views.mis_partidos, name='mis_partidos'),
    path('partidos/<int:reserva_pk>/registrar/', views.crear_resultado, name='crear_resultado'),
    path('partidos/<int:pk>/confirmar/', views.confirmar_resultado, name='confirmar_resultado'),
    path('partidos/<int:pk>/disputar/', views.disputar_resultado, name='disputar_resultado'),
]
