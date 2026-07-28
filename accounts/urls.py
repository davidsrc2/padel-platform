from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginRateLimitView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro/', views.registro, name='registro'),
    path('crear-comunidad/', views.crear_comunidad, name='crear_comunidad'),
    path('perfil/', views.perfil, name='perfil'),
    path('push/suscribir/', views.push_suscribir, name='push_suscribir'),
    path('push/desuscribir/', views.push_desuscribir, name='push_desuscribir'),
    path('ajax/portales/', views.portales_ajax, name='portales_ajax'),
    path('ajax/viviendas/', views.viviendas_ajax, name='viviendas_ajax'),

    path('password-reset/', views.PasswordResetRateLimitView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
]
