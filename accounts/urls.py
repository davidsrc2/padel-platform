from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro/', views.registro, name='registro'),
    path('ajax/portales/', views.portales_ajax, name='portales_ajax'),
    path('ajax/viviendas/', views.viviendas_ajax, name='viviendas_ajax'),
]
