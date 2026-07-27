from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta, datetime

from panel.permisos import limitar_a_urbanizacion, panel_required, resolver_urbanizacion
from .estadisticas import calcular_estadisticas
from .models import Reserva, ResultadoPartido
from .forms import ReservaForm, ResultadoPartidoForm
from .emails import enviar_confirmacion_reserva, enviar_cancelacion_reserva
from pistas.models import BloqueoPista, Pista
from urbanizaciones.models import Urbanizacion


def _franjas_disponibles(pista, fecha):
    urb = pista.urbanizacion
    franjas = []
    apertura = datetime.combine(fecha, urb.hora_apertura)
    cierre = datetime.combine(fecha, urb.hora_cierre)
    duracion = timedelta(minutes=urb.duracion_franja_minutos)
    reservas_por_hora = {
        r.hora_inicio: r
        for r in Reserva.objects.filter(
            pista=pista, fecha=fecha, estado=Reserva.ESTADO_CONFIRMADA
        ).select_related('usuario')
    }
    bloqueos = list(BloqueoPista.objects.filter(pista=pista, fecha=fecha))
    ahora = timezone.localtime().replace(tzinfo=None)
    actual = apertura
    while actual + duracion <= cierre:
        hora_inicio = actual.time()
        hora_fin = (actual + duracion).time()
        reserva = reservas_por_hora.get(hora_inicio)
        bloqueo = next(
            (b for b in bloqueos if b.hora_inicio < hora_fin and b.hora_fin > hora_inicio), None
        )
        franjas.append({
            'hora_inicio': hora_inicio,
            'hora_fin': hora_fin,
            'ocupada': reserva is not None,
            'bloqueada': bloqueo is not None,
            'motivo_bloqueo': bloqueo.motivo if bloqueo else '',
            'pasada': actual + duracion <= ahora,
            'reservado_por': reserva.usuario if reserva else None,
            'companeros': reserva.companeros if reserva else '',
        })
        actual += duracion
    return franjas


def _libres_dia(pistas, dia):
    return sum(
        1
        for pista in pistas
        for franja in _franjas_disponibles(pista, dia)
        if not franja['ocupada'] and not franja['bloqueada'] and not franja['pasada']
    )


def _resumen_semana(pistas, hoy, max_fecha):
    """Cuenta franjas libres por día, para el selector de semana del calendario."""
    dias = (max_fecha - hoy).days + 1
    resumen = []
    for i in range(min(dias, 7)):
        dia = hoy + timedelta(days=i)
        resumen.append({'fecha': dia, 'libres': _libres_dia(pistas, dia)})
    return resumen


@login_required
def calendario(request):
    usuario = request.user
    if not usuario.aprobado:
        return render(request, 'reservas/pendiente_aprobacion.html')

    urb = usuario.urbanizacion
    urbanizaciones = None
    if not urb and usuario.rol == usuario.ROL_SUPERADMIN:
        urbanizaciones = Urbanizacion.objects.order_by('nombre')
        urb_id = request.GET.get('urbanizacion')
        urb = urbanizaciones.filter(pk=urb_id).first() if urb_id else urbanizaciones.first()

    if not urb:
        if usuario.rol == usuario.ROL_SUPERADMIN:
            messages.error(request, 'No hay ninguna urbanización creada todavía.')
            return redirect('accounts:login')
        messages.error(request, 'No tienes una urbanización asignada.')
        return redirect('accounts:login')

    hoy = timezone.localdate()
    fecha_str = request.GET.get('fecha', str(hoy))
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        fecha = hoy

    fecha = max(hoy, min(fecha, hoy + timedelta(days=urb.antelacion_maxima_dias)))

    pistas = list(urb.pistas.filter(activa=True))
    calendario_data = [
        {'pista': p, 'franjas': _franjas_disponibles(p, fecha)}
        for p in pistas
    ]
    max_fecha = hoy + timedelta(days=urb.antelacion_maxima_dias)

    context = {
        'fecha': fecha,
        'max_fecha': max_fecha,
        'semana': _resumen_semana(pistas, hoy, max_fecha),
        'calendario': calendario_data,
        'urb': urb,
        'urbanizaciones': urbanizaciones,
    }
    return render(request, 'reservas/calendario.html', context)


def _respuesta_franja_htmx(request, usuario, pista_id, fecha, hora_inicio, error=None):
    """Recalcula el estado real de una franja y la de su día en la tira semanal,
    y devuelve ambos parciales (el segundo como out-of-band swap) para htmx."""
    pista = get_object_or_404(Pista, pk=pista_id)
    franjas = _franjas_disponibles(pista, fecha)
    franja = next((f for f in franjas if f['hora_inicio'] == hora_inicio), None)
    if franja and error and not franja['ocupada'] and not franja['bloqueada']:
        franja['error'] = error

    html = render_to_string('reservas/_franja.html', {
        'pista': pista, 'fecha': fecha, 'franja': franja,
    }, request=request)

    urb = pista.urbanizacion
    if usuario.rol != usuario.ROL_SUPERADMIN or usuario.urbanizacion:
        pistas_urb = list(urb.pistas.filter(activa=True))
        libres = _libres_dia(pistas_urb, fecha)
        html += render_to_string('reservas/_dia_tab.html', {
            'dia': {'fecha': fecha, 'libres': libres},
            'fecha_actual': fecha,
            'urb_pk': urb.pk,
            'mostrar_urb_param': usuario.rol == usuario.ROL_SUPERADMIN,
            'oob': True,
        }, request=request)

    return HttpResponse(html)


@login_required
def crear_reserva(request):
    usuario = request.user
    es_htmx = request.headers.get('HX-Request') == 'true'

    if not usuario.aprobado:
        # No debería poder llegar aquí desde la UI (el calendario ni se
        # renderiza sin aprobación), pero por si llega una petición directa.
        if not es_htmx:
            messages.error(request, 'Tu cuenta no ha sido aprobada aún.')
        return redirect('reservas:calendario')

    if request.method == 'POST':
        form = ReservaForm(request.POST, usuario=usuario)
        if usuario.rol == usuario.ROL_SUPERADMIN:
            form.fields['pista'].queryset = Pista.objects.all()

        error = None
        reserva = None
        if form.is_valid():
            try:
                reserva = form.save()
                enviar_confirmacion_reserva(reserva)
            except ValidationError as e:
                error = ' '.join(e.messages)
        else:
            error = ' '.join(err for errores in form.errors.values() for err in errores)

        if es_htmx:
            pista_id = request.POST.get('pista')
            fecha_str = request.POST.get('fecha')
            hora_inicio_str = request.POST.get('hora_inicio')
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M:%S').time()
            except (TypeError, ValueError):
                return redirect('reservas:calendario')
            return _respuesta_franja_htmx(request, usuario, pista_id, fecha, hora_inicio, error=error)

        if reserva:
            messages.success(
                request,
                f'Reserva confirmada: {reserva.fecha} '
                f'{reserva.hora_inicio.strftime("%H:%M")}–{reserva.hora_fin.strftime("%H:%M")}.'
            )
        elif error:
            messages.error(request, error)

    return redirect('reservas:calendario')


@login_required
def mis_reservas(request):
    usuario = request.user
    reservas = Reserva.objects.filter(
        usuario=usuario,
        estado=Reserva.ESTADO_CONFIRMADA,
        fecha__gte=timezone.localdate(),
    ).select_related('pista', 'pista__urbanizacion')
    pasadas = Reserva.objects.filter(
        usuario=usuario,
        fecha__lt=timezone.localdate(),
    ).order_by('-fecha', '-hora_inicio').select_related('pista')[:20]
    return render(request, 'reservas/mis_reservas.html', {'reservas': reservas, 'pasadas': pasadas})


@login_required
def cancelar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk, usuario=request.user, estado=Reserva.ESTADO_CONFIRMADA)
    es_htmx = request.headers.get('HX-Request') == 'true'

    if not reserva.puede_cancelar():
        mensaje = f'No puedes cancelar con menos de {reserva.urbanizacion.cancelacion_minima_horas}h de antelación.'
        if es_htmx:
            return render(request, 'reservas/_reserva_proxima.html', {'r': reserva, 'error': mensaje})
        messages.error(request, mensaje)
        return redirect('reservas:mis_reservas')

    if request.method == 'POST':
        reserva.estado = Reserva.ESTADO_CANCELADA
        reserva.save()
        enviar_cancelacion_reserva(reserva)
        if es_htmx:
            return render(request, 'reservas/_reserva_cancelada.html', {'r': reserva})
        messages.success(request, 'Reserva cancelada.')
    return redirect('reservas:mis_reservas')


@login_required
def editar_companeros(request, pk):
    reserva = get_object_or_404(
        Reserva, pk=pk, usuario=request.user, estado=Reserva.ESTADO_CONFIRMADA,
        fecha__gte=timezone.localdate(),
    )
    es_htmx = request.headers.get('HX-Request') == 'true'

    if request.method == 'POST':
        reserva.companeros = request.POST.get('companeros', '').strip()[:200]
        reserva.save(update_fields=['companeros'])
        if not es_htmx:
            messages.success(request, 'Actualizado.')

    if es_htmx:
        return render(request, 'reservas/_reserva_proxima.html', {'r': reserva})
    return redirect('reservas:mis_reservas')


def _partidos_pendientes_de(usuario):
    ahora = timezone.now()
    candidatas = Reserva.objects.filter(
        usuario=usuario, estado=Reserva.ESTADO_CONFIRMADA,
    ).exclude(resultado__isnull=False).select_related('pista')
    return [
        r for r in candidatas
        if timezone.make_aware(datetime.combine(r.fecha, r.hora_fin)) < ahora
    ]


@login_required
def mis_partidos(request):
    usuario = request.user
    pendientes = _partidos_pendientes_de(usuario)
    resultados = (
        ResultadoPartido.objects.filter(Q(equipo_a=usuario) | Q(equipo_b=usuario))
        .distinct()
        .select_related('reserva', 'reserva__pista')
        .prefetch_related('sets', 'equipo_a', 'equipo_b')
        .order_by('-reserva__fecha', '-reserva__hora_inicio')
    )
    # gano() exige el usuario cuyo resultado se consulta, así que no se puede
    # llamar como `r.gano` desde la plantilla (Django no la invoca si requiere
    # argumentos) — se precalcula aquí para la perspectiva de quien mira la página.
    for r in resultados:
        r.gano_propio = r.gano(usuario)
    stats = calcular_estadisticas(usuario)
    return render(request, 'reservas/mis_partidos.html', {
        'pendientes': pendientes,
        'resultados': resultados,
        'stats': stats,
    })


@login_required
def crear_resultado(request, reserva_pk):
    usuario = request.user
    reserva = get_object_or_404(
        Reserva, pk=reserva_pk, usuario=usuario, estado=Reserva.ESTADO_CONFIRMADA,
    )
    fin_dt = timezone.make_aware(datetime.combine(reserva.fecha, reserva.hora_fin))
    if fin_dt > timezone.now():
        messages.error(request, 'Todavía no ha terminado esta reserva.')
        return redirect('reservas:mis_partidos')
    if hasattr(reserva, 'resultado'):
        messages.error(request, 'Esta reserva ya tiene un resultado registrado.')
        return redirect('reservas:mis_partidos')

    if request.method == 'POST':
        form = ResultadoPartidoForm(request.POST, usuario=usuario, reserva=reserva)
        if form.is_valid():
            form.save()
            messages.success(request, 'Resultado registrado. Queda pendiente de que el rival lo confirme.')
            return redirect('reservas:mis_partidos')
    else:
        form = ResultadoPartidoForm(usuario=usuario, reserva=reserva)

    return render(request, 'reservas/crear_resultado.html', {'form': form, 'reserva': reserva})


@login_required
def confirmar_resultado(request, pk):
    resultado = get_object_or_404(ResultadoPartido, pk=pk, estado=ResultadoPartido.ESTADO_PENDIENTE)
    if not resultado.equipo_b.filter(pk=request.user.pk).exists():
        messages.error(request, 'Solo un jugador del equipo rival puede confirmar este resultado.')
        return redirect('reservas:mis_partidos')
    if request.method == 'POST':
        resultado.estado = ResultadoPartido.ESTADO_CONFIRMADO
        resultado.confirmado_por = request.user
        resultado.fecha_confirmacion = timezone.now()
        resultado.save()
        messages.success(request, 'Resultado confirmado.')
    return redirect('reservas:mis_partidos')


@login_required
def disputar_resultado(request, pk):
    resultado = get_object_or_404(ResultadoPartido, pk=pk, estado=ResultadoPartido.ESTADO_PENDIENTE)
    if not resultado.equipo_b.filter(pk=request.user.pk).exists():
        messages.error(request, 'Solo un jugador del equipo rival puede disputar este resultado.')
        return redirect('reservas:mis_partidos')
    if request.method == 'POST':
        resultado.estado = ResultadoPartido.ESTADO_DISPUTADO
        resultado.save()
        messages.warning(request, 'Resultado marcado como disputado. Un administrador lo revisará.')
    return redirect('reservas:mis_partidos')


@panel_required
def panel_resultados(request):
    urb, urbanizaciones = resolver_urbanizacion(request)
    if not urb:
        messages.error(request, 'No hay ninguna urbanización creada todavía.')
        return redirect('panel:inicio')

    base = ResultadoPartido.objects.filter(reserva__pista__urbanizacion=urb).select_related(
        'reserva', 'reserva__pista', 'creado_por'
    ).prefetch_related('sets', 'equipo_a', 'equipo_b')

    return render(request, 'panel/resultados.html', {
        'urb': urb,
        'urbanizaciones': urbanizaciones,
        'disputados': base.filter(estado=ResultadoPartido.ESTADO_DISPUTADO),
        'pendientes': base.filter(estado=ResultadoPartido.ESTADO_PENDIENTE),
    })


@panel_required
def panel_resultado_resolver(request, pk):
    resultado = get_object_or_404(
        limitar_a_urbanizacion(request, ResultadoPartido.objects.all(), campo='reserva__pista__urbanizacion'),
        pk=pk,
    )
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'confirmar':
            resultado.estado = ResultadoPartido.ESTADO_CONFIRMADO
            resultado.confirmado_por = request.user
            resultado.fecha_confirmacion = timezone.now()
            resultado.save()
            messages.success(request, 'Resultado confirmado por el administrador.')
        elif accion == 'eliminar':
            resultado.delete()
            messages.success(request, 'Resultado eliminado. Se puede volver a registrar.')
    return redirect(request.META.get('HTTP_REFERER') or 'panel:resultados')
