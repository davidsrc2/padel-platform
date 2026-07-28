from django.urls import path

from . import views

app_name = 'social'

urlpatterns = [
    path('vecinos/', views.directorio, name='directorio'),
    path('vecinos/<int:pk>/seguir/', views.seguir, name='seguir'),
    path('vecinos/<int:pk>/dejar-de-seguir/', views.dejar_de_seguir, name='dejar_de_seguir'),
    path('feed/', views.feed, name='feed'),
]
