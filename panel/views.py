from django.shortcuts import render

from accounts.models import Usuario
from pistas.models import Pista
from viviendas.models import Portal

from .permisos import panel_required, resolver_urbanizacion


@panel_required
def inicio(request):
    urb, urbanizaciones = resolver_urbanizacion(request)
    contexto = {'urb': urb, 'urbanizaciones': urbanizaciones}

    if urb:
        contexto.update({
            'n_pendientes': Usuario.objects.filter(vivienda__portal__urbanizacion=urb, aprobado=False).count(),
            'n_vecinos': Usuario.objects.filter(vivienda__portal__urbanizacion=urb, aprobado=True).count(),
            'n_portales': Portal.objects.filter(urbanizacion=urb).count(),
            'n_pistas': Pista.objects.filter(urbanizacion=urb).count(),
        })

    return render(request, 'panel/inicio.html', contexto)
