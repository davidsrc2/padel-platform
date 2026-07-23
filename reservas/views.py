from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime

from .models import Reserva
from .forms import ReservaForm
from pistas.models import Pista


def _franjas_disponibles(pista, fecha):
    urb = pista.urbanizacion
    franjas = []
    apertura = datetime.combine(fecha, urb.hora_apertura)
    cierre = datetime.combine(fecha, urb.hora_cierre)
    duracion = timedelta(minutes=urb.duracion_franja_minutos)
    reservadas = set(
        Reserva.objects.filter(
            pista=pista, fecha=fecha, estado=Reserva.ESTADO_CONFIRMADA
        ).values_list('hora_inicio', flat=True)
    )
    actual = apertura
    while actual + duracion <= cierre:
        franjas.append({
            'hora_inicio': actual.time(),
            'hora_fin': (actual + duracion).time(),
            'ocupada': actual.time() in reservadas,
        })
        actual += duracion
    return franjas


@login_required
def calendario(request):
    usuario = request.user
    if not usuario.aprobado:
        return render(request, 'reservas/pendiente_aprobacion.html')

    urb = usuario.urbanizacion
    if not urb:
        messages.error(request, 'No tienes una urbanización asignada.')
        return redirect('accounts:login')

    hoy = timezone.localdate()
    fecha_str = request.GET.get('fecha', str(hoy))
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        fecha = hoy

    fecha = max(hoy, min(fecha, hoy + timedelta(days=urb.antelacion_maxima_dias)))

    pistas = urb.pistas.filter(activa=True)
    calendario_data = [
        {'pista': p, 'franjas': _franjas_disponibles(p, fecha)}
        for p in pistas
    ]

    context = {
        'fecha': fecha,
        'prev_fecha': fecha - timedelta(days=1) if fecha > hoy else None,
        'next_fecha': fecha + timedelta(days=1) if fecha < hoy + timedelta(days=urb.antelacion_maxima_dias) else None,
        'calendario': calendario_data,
        'urb': urb,
    }
    return render(request, 'reservas/calendario.html', context)


@login_required
def crear_reserva(request):
    usuario = request.user
    if not usuario.aprobado:
        messages.error(request, 'Tu cuenta no ha sido aprobada aún.')
        return redirect('reservas:calendario')

    if request.method == 'POST':
        pista_id = request.POST.get('pista')
        fecha_str = request.POST.get('fecha')
        hora_inicio_str = request.POST.get('hora_inicio')

        try:
            pista = Pista.objects.get(pk=pista_id, urbanizacion=usuario.urbanizacion)
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M:%S').time()
        except Exception:
            messages.error(request, 'Datos de reserva incorrectos.')
            return redirect('reservas:calendario')

        urb = pista.urbanizacion
        duracion = timedelta(minutes=urb.duracion_franja_minutos)
        hora_fin = (datetime.combine(fecha, hora_inicio) + duracion).time()

        reserva = Reserva(pista=pista, usuario=usuario, fecha=fecha, hora_inicio=hora_inicio, hora_fin=hora_fin)
        try:
            reserva.full_clean()
            reserva.save()
            messages.success(request, f'Reserva confirmada: {fecha} {hora_inicio.strftime("%H:%M")}–{hora_fin.strftime("%H:%M")}.')
        except Exception as e:
            messages.error(request, str(e))

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
        messages.success(request, 'Reserva cancelada.')
    return redirect('reservas:mis_reservas')
