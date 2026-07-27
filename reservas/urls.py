from django.urls import path
from . import views

app_name = 'reservas'

urlpatterns = [
    path('', views.calendario, name='calendario'),
    path('reservar/', views.crear_reserva, name='crear'),
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('cancelar/<int:pk>/', views.cancelar_reserva, name='cancelar'),
    path('companeros/<int:pk>/', views.editar_companeros, name='editar_companeros'),
]
