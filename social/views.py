from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Usuario
from reservas.models import Participante, ResultadoPartido

from .models import Seguimiento


@login_required
def directorio(request):
    usuario = request.user
    if usuario.urbanizacion:
        vecinos = list(
            Usuario.objects.filter(
                vivienda__portal__urbanizacion=usuario.urbanizacion, aprobado=True,
            ).exclude(pk=usuario.pk).order_by('first_name', 'username')
        )
    else:
        vecinos = []

    siguiendo_ids = set(Seguimiento.objects.filter(seguidor=usuario).values_list('seguido_id', flat=True))
    for v in vecinos:
        v.le_sigo = v.pk in siguiendo_ids

    return render(request, 'social/directorio.html', {
        'vecinos': vecinos,
        'n_seguidores': usuario.seguidores.count(),
        'n_siguiendo': usuario.siguiendo.count(),
    })


@login_required
def seguir(request, pk):
    objetivo = get_object_or_404(Usuario, pk=pk, aprobado=True)
    if request.method == 'POST':
        if objetivo.pk == request.user.pk:
            messages.error(request, 'No puedes seguirte a ti mismo.')
        elif objetivo.urbanizacion != request.user.urbanizacion:
            messages.error(request, 'Solo puedes seguir a vecinos de tu urbanización.')
        else:
            Seguimiento.objects.get_or_create(seguidor=request.user, seguido=objetivo)
            messages.success(request, f'Ahora sigues a {objetivo.get_full_name() or objetivo.username}.')
    return redirect(request.META.get('HTTP_REFERER') or 'social:directorio')


@login_required
def dejar_de_seguir(request, pk):
    if request.method == 'POST':
        Seguimiento.objects.filter(seguidor=request.user, seguido_id=pk).delete()
        messages.success(request, 'Has dejado de seguir.')
    return redirect(request.META.get('HTTP_REFERER') or 'social:directorio')


@login_required
def feed(request):
    seguidos_ids = Seguimiento.objects.filter(seguidor=request.user).values_list('seguido_id', flat=True)
    resultados = list(
        ResultadoPartido.objects.filter(
            participantes__usuario_id__in=seguidos_ids,
            estado=ResultadoPartido.ESTADO_CONFIRMADO,
        )
        .distinct()
        .select_related('reserva', 'reserva__pista')
        .prefetch_related('sets', 'participantes', 'participantes__usuario')
        .order_by('-fecha_confirmacion')[:30]
    )
    # jugadores(equipo) exige un argumento, así que no se puede llamar desde
    # la plantilla como `r.jugadores` — se precalcula aquí.
    for r in resultados:
        r.equipo_a_jugadores = r.jugadores(Participante.EQUIPO_A)
        r.equipo_b_jugadores = r.jugadores(Participante.EQUIPO_B)

    return render(request, 'social/feed.html', {'resultados': resultados})
