import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from panel.permisos import limitar_a_urbanizacion, panel_required, resolver_urbanizacion
from .emails import enviar_aprobacion_usuario
from .forms import CrearComunidadForm, PerfilForm, RegistroForm
from .models import PushSubscription, Usuario
from viviendas.models import Portal, Vivienda


def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro enviado. El administrador debe aprobarlo antes de que puedas acceder.')
            return redirect('accounts:login')
    else:
        form = RegistroForm()
    return render(request, 'accounts/registro.html', {'form': form})


@login_required
def crear_comunidad(request):
    if request.user.rol != Usuario.ROL_SUPERADMIN:
        messages.error(request, 'Solo el superadmin puede dar de alta una comunidad nueva.')
        return redirect('reservas:calendario')

    if request.method == 'POST':
        form = CrearComunidadForm(request.POST)
        if form.is_valid():
            admin = form.save()
            messages.success(
                request,
                f'"{admin.urbanizacion.nombre}" creada, con "{admin.username}" como administrador.',
            )
            return redirect(f"{reverse('panel:inicio')}?urbanizacion={admin.urbanizacion.pk}")
    else:
        form = CrearComunidadForm()
    return render(request, 'accounts/crear_comunidad.html', {'form': form})


@login_required
def perfil(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado.')
            return redirect('accounts:perfil')
    else:
        form = PerfilForm(instance=request.user)
    return render(request, 'accounts/perfil.html', {'usuario': request.user, 'form': form})


@panel_required
def panel_usuarios(request):
    urb, urbanizaciones = resolver_urbanizacion(request)
    if not urb:
        messages.error(request, 'No hay ninguna urbanización creada todavía.')
        return redirect('panel:inicio')

    base = Usuario.objects.filter(vivienda__portal__urbanizacion=urb).select_related(
        'vivienda', 'vivienda__portal'
    )
    pendientes = base.filter(aprobado=False).order_by('date_joined')
    aprobados = base.filter(aprobado=True).order_by('-date_joined')

    return render(request, 'panel/usuarios.html', {
        'urb': urb,
        'urbanizaciones': urbanizaciones,
        'pendientes': pendientes,
        'aprobados': aprobados,
    })


@panel_required
def panel_usuario_aprobar(request, pk):
    usuario = get_object_or_404(
        limitar_a_urbanizacion(request, Usuario.objects.all(), campo='vivienda__portal__urbanizacion'), pk=pk
    )
    if request.method == 'POST':
        usuario.aprobado = True
        usuario.save()
        enviar_aprobacion_usuario(usuario)
        messages.success(request, f'{usuario.get_full_name() or usuario.username} aprobado. Se le ha enviado un email.')
    return redirect(request.META.get('HTTP_REFERER') or 'panel:usuarios')


@panel_required
def panel_usuario_rechazar(request, pk):
    usuario = get_object_or_404(
        limitar_a_urbanizacion(request, Usuario.objects.all(), campo='vivienda__portal__urbanizacion'),
        pk=pk, aprobado=False,
    )
    if request.method == 'POST':
        nombre = usuario.get_full_name() or usuario.username
        usuario.delete()
        messages.success(request, f'Solicitud de {nombre} rechazada y eliminada.')
    return redirect(request.META.get('HTTP_REFERER') or 'panel:usuarios')


@login_required
@require_POST
def push_suscribir(request):
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False}, status=400)

    endpoint = data.get('endpoint')
    claves = data.get('keys', {})
    if not endpoint or not claves.get('p256dh') or not claves.get('auth'):
        return JsonResponse({'ok': False}, status=400)

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'usuario': request.user, 'p256dh': claves['p256dh'], 'auth': claves['auth']},
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def push_desuscribir(request):
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        data = {}

    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.objects.filter(usuario=request.user, endpoint=endpoint).delete()
    else:
        PushSubscription.objects.filter(usuario=request.user).delete()
    return JsonResponse({'ok': True})


def portales_ajax(request):
    from django.http import JsonResponse
    urb_id = request.GET.get('urbanizacion_id')
    portales = Portal.objects.filter(urbanizacion_id=urb_id).values('id', 'nombre')
    return JsonResponse({'portales': list(portales)})


def viviendas_ajax(request):
    from django.http import JsonResponse
    portal_id = request.GET.get('portal_id')
    viviendas = Vivienda.objects.filter(portal_id=portal_id).values('id', 'piso', 'puerta')
    data = [{'id': v['id'], 'label': f"{v['piso']}{'-'+v['puerta'] if v['puerta'] else ''}"} for v in viviendas]
    return JsonResponse({'viviendas': data})
