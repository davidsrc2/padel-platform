from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from panel.permisos import limitar_a_urbanizacion, panel_required, resolver_urbanizacion
from .forms import PortalForm, ViviendaForm
from .models import Portal, Vivienda


@panel_required
def panel_portales(request):
    urb, urbanizaciones = resolver_urbanizacion(request)
    if not urb:
        messages.error(request, 'No hay ninguna urbanización creada todavía.')
        return redirect('panel:inicio')

    portales = Portal.objects.filter(urbanizacion=urb).prefetch_related('viviendas').order_by('nombre')
    return render(request, 'panel/portales.html', {
        'urb': urb,
        'urbanizaciones': urbanizaciones,
        'portales': portales,
        'portal_form': PortalForm(auto_id=False),
        # auto_id=False: este form se re-renderiza una vez por portal en la
        # plantilla, con auto_id se repetiría el mismo id="id_piso" en cada uno.
        'vivienda_form': ViviendaForm(auto_id=False),
    })


@panel_required
def panel_portal_crear(request):
    urb, _ = resolver_urbanizacion(request)
    if request.method == 'POST' and urb:
        form = PortalForm(request.POST, urbanizacion=urb)
        if form.is_valid():
            try:
                portal = form.save()
                messages.success(request, f'Portal "{portal.nombre}" creado.')
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
        else:
            for errores in form.errors.values():
                for error in errores:
                    messages.error(request, error)
    return redirect(request.META.get('HTTP_REFERER') or 'panel:portales')


@panel_required
def panel_portal_eliminar(request, pk):
    portal = get_object_or_404(limitar_a_urbanizacion(request, Portal.objects.all()), pk=pk)
    if request.method == 'POST':
        nombre = portal.nombre
        n_viviendas = portal.viviendas.count()
        portal.delete()
        if n_viviendas:
            messages.success(request, f'Portal "{nombre}" eliminado, junto con sus {n_viviendas} vivienda(s).')
        else:
            messages.success(request, f'Portal "{nombre}" eliminado.')
    return redirect(request.META.get('HTTP_REFERER') or 'panel:portales')


@panel_required
def panel_vivienda_crear(request, portal_pk):
    portal = get_object_or_404(limitar_a_urbanizacion(request, Portal.objects.all()), pk=portal_pk)
    if request.method == 'POST':
        form = ViviendaForm(request.POST, portal=portal)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Vivienda añadida a Portal {portal.nombre}.')
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
        else:
            for errores in form.errors.values():
                for error in errores:
                    messages.error(request, error)
    return redirect(request.META.get('HTTP_REFERER') or 'panel:portales')


@panel_required
def panel_vivienda_eliminar(request, pk):
    vivienda = get_object_or_404(
        limitar_a_urbanizacion(request, Vivienda.objects.all(), campo='portal__urbanizacion'), pk=pk
    )
    if request.method == 'POST':
        descripcion = str(vivienda)
        vivienda.delete()
        messages.success(request, f'{descripcion} eliminada.')
    return redirect(request.META.get('HTTP_REFERER') or 'panel:portales')
