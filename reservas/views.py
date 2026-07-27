from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, datetime

from .models import Reserva
from .forms import ReservaForm
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


def _resumen_semana(pistas, hoy, max_fecha):
    """Cuenta franjas libres por día, para el selector de semana del calendario."""
    dias = (max_fecha - hoy).days + 1
    resumen = []
    for i in range(min(dias, 7)):
        dia = hoy + timedelta(days=i)
        libres = sum(
            1
            for pista in pistas
            for franja in _franjas_disponibles(pista, dia)
            if not franja['ocupada'] and not franja['bloqueada'] and not franja['pasada']
        )
        resumen.append({'fecha': dia, 'libres': libres})
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


@login_required
def crear_reserva(request):
    usuario = request.user
    if not usuario.aprobado:
        messages.error(request, 'Tu cuenta no ha sido aprobada aún.')
        return redirect('reservas:calendario')

    if request.method == 'POST':
        form = ReservaForm(request.POST, usuario=usuario)
        if usuario.rol == usuario.ROL_SUPERADMIN:
            form.fields['pista'].queryset = Pista.objects.all()

        if form.is_valid():
            try:
                reserva = form.save()
                messages.success(
                    request,
                    f'Reserva confirmada: {reserva.fecha} '
                    f'{reserva.hora_inicio.strftime("%H:%M")}–{reserva.hora_fin.strftime("%H:%M")}.'
                )
                enviar_confirmacion_reserva(reserva)
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
        else:
            for errores in form.errors.values():
                for error in errores:
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
    if not reserva.puede_cancelar():
        messages.error(request, f'No puedes cancelar con menos de {reserva.urbanizacion.cancelacion_minima_horas}h de antelación.')
        return redirect('reservas:mis_reservas')
    if request.method == 'POST':
        reserva.estado = Reserva.ESTADO_CANCELADA
        reserva.save()
        enviar_cancelacion_reserva(reserva)
        messages.success(request, 'Reserva cancelada.')
    return redirect('reservas:mis_reservas')


@login_required
def editar_companeros(request, pk):
    reserva = get_object_or_404(
        Reserva, pk=pk, usuario=request.user, estado=Reserva.ESTADO_CONFIRMADA,
        fecha__gte=timezone.localdate(),
    )
    if request.method == 'POST':
        reserva.companeros = request.POST.get('companeros', '').strip()[:200]
        reserva.save(update_fields=['companeros'])
        messages.success(request, 'Actualizado.')
    return redirect('reservas:mis_reservas')
