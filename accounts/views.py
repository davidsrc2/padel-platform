from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from panel.permisos import limitar_a_urbanizacion, panel_required, resolver_urbanizacion
from .emails import enviar_aprobacion_usuario
from .forms import RegistroForm
from .models import Usuario
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
def perfil(request):
    return render(request, 'accounts/perfil.html', {'usuario': request.user})


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
