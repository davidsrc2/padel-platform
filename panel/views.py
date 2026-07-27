from datetime import timedelta

from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import Usuario
from pistas.models import Pista
from reservas.models import Reserva, ResultadoPartido
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
            'n_disputados': ResultadoPartido.objects.filter(
                reserva__pista__urbanizacion=urb, estado=ResultadoPartido.ESTADO_DISPUTADO,
            ).count(),
        })

    return render(request, 'panel/inicio.html', contexto)


@panel_required
def estadisticas(request):
    urb, urbanizaciones = resolver_urbanizacion(request)
    if not urb:
        return redirect('panel:inicio')

    base = Reserva.objects.filter(pista__urbanizacion=urb, estado=Reserva.ESTADO_CONFIRMADA)
    hace_30_dias = timezone.localdate() - timedelta(days=30)

    top_vecinos = (
        base.values('usuario_id', 'usuario__first_name', 'usuario__last_name', 'usuario__username')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )
    for v in top_vecinos:
        v['nombre'] = (
            f"{v['usuario__first_name']} {v['usuario__last_name']}".strip()
            or v['usuario__username']
        )

    contexto = {
        'urb': urb,
        'urbanizaciones': urbanizaciones,
        'total_reservas': base.count(),
        'reservas_ultimos_30_dias': base.filter(fecha__gte=hace_30_dias).count(),
        'top_pistas': base.values('pista__nombre').annotate(total=Count('id')).order_by('-total')[:5],
        'top_franjas': base.values('hora_inicio').annotate(total=Count('id')).order_by('-total')[:5],
        'top_vecinos': top_vecinos,
    }
    return render(request, 'panel/estadisticas.html', contexto)
