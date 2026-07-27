from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.shortcuts import redirect


def service_worker(request):
    # Se sirve desde la raíz (no desde /static/) para que su scope por
    # defecto cubra todo el sitio, no solo la carpeta de estáticos.
    contenido = (Path(settings.BASE_DIR) / 'static' / 'sw.js').read_text()
    return HttpResponse(contenido, content_type='application/javascript')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('reservas/', include('reservas.urls')),
    path('panel/', include('panel.urls')),
    path('sw.js', service_worker, name='sw'),
    path('', lambda request: redirect('reservas:calendario')),
]
