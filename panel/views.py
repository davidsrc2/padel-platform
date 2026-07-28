from datetime import timedelta

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import Usuario
from pistas.models import Pista
from reservas.models import Reserva, ResultadoPartido
from urbanizaciones.models import Urbanizacion
from viviendas.models import Portal

from .permisos import panel_required, resolver_urbanizacion


@panel_required
def inicio(request):
    urb, urbanizaciones = resolver_urbanizacion(request)
    contexto = {'urb': urb, 'urbanizaciones': urbanizaciones}

    if urb:
        hoy = timezone.localdate()
        reservas_urb = Reserva.objects.filter(pista__urbanizacion=urb, estado=Reserva.ESTADO_CONFIRMADA)
        contexto.update({
            'n_pendientes': Usuario.objects.filter(vivienda__portal__urbanizacion=urb, aprobado=False).count(),
            'n_vecinos': Usuario.objects.filter(vivienda__portal__urbanizacion=urb, aprobado=True).count(),
            'n_portales': Portal.objects.filter(urbanizacion=urb).count(),
            'n_pistas': Pista.objects.filter(urbanizacion=urb).count(),
            'n_disputados': ResultadoPartido.objects.filter(
                reserva__pista__urbanizacion=urb, estado=ResultadoPartido.ESTADO_DISPUTADO,
            ).count(),
            'n_resultados_pendientes': ResultadoPartido.objects.filter(
                reserva__pista__urbanizacion=urb, estado=ResultadoPartido.ESTADO_PENDIENTE,
            ).count(),
            'reservas_hoy': reservas_urb.filter(fecha=hoy).count(),
            'reservas_semana': reservas_urb.filter(fecha__gte=hoy, fecha__lt=hoy + timedelta(days=7)).count(),
            'actividad_reciente': Reserva.objects.filter(pista__urbanizacion=urb)
                .select_related('usuario', 'pista').order_by('-creada')[:6],
        })

    return render(request, 'panel/inicio.html', contexto)


@panel_required
def superadmin_overview(request):
    if request.user.rol != Usuario.ROL_SUPERADMIN:
        messages.error(request, 'Solo el superadmin puede ver esta página.')
        return redirect('panel:inicio')

    query = request.GET.get('q', '').strip()
    urbanizaciones = Urbanizacion.objects.order_by('nombre')
    if query:
        urbanizaciones = urbanizaciones.filter(nombre__icontains=query)

    hace_30_dias = timezone.localdate() - timedelta(days=30)

    comunidades = []
    for urb in urbanizaciones:
        comunidades.append({
            'urb': urb,
            'n_vecinos': Usuario.objects.filter(vivienda__portal__urbanizacion=urb, aprobado=True).count(),
            'n_pendientes': Usuario.objects.filter(vivienda__portal__urbanizacion=urb, aprobado=False).count(),
            'n_pistas': Pista.objects.filter(urbanizacion=urb).count(),
            'n_disputados': ResultadoPartido.objects.filter(
                reserva__pista__urbanizacion=urb, estado=ResultadoPartido.ESTADO_DISPUTADO,
            ).count(),
            'reservas_30d': Reserva.objects.filter(
                pista__urbanizacion=urb, estado=Reserva.ESTADO_CONFIRMADA, fecha__gte=hace_30_dias,
            ).count(),
        })

    contexto = {
        'query': query,
        'comunidades': comunidades,
        'n_urbanizaciones': Urbanizacion.objects.count(),
        'n_vecinos_total': Usuario.objects.filter(rol=Usuario.ROL_VECINO, aprobado=True).count(),
        'n_reservas_30d_total': Reserva.objects.filter(
            estado=Reserva.ESTADO_CONFIRMADA, fecha__gte=hace_30_dias,
        ).count(),
    }
    return render(request, 'panel/superadmin_overview.html', contexto)


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
