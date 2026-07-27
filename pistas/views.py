from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from panel.permisos import limitar_a_urbanizacion, panel_required, resolver_urbanizacion
from .forms import PistaForm
from .models import Pista


@panel_required
def panel_pistas(request):
    urb, urbanizaciones = resolver_urbanizacion(request)
    if not urb:
        messages.error(request, 'No hay ninguna urbanización creada todavía.')
        return redirect('panel:inicio')

    pistas = Pista.objects.filter(urbanizacion=urb).order_by('nombre')
    return render(request, 'panel/pistas.html', {
        'urb': urb,
        'urbanizaciones': urbanizaciones,
        'pistas': pistas,
        'pista_form': PistaForm(),
    })


@panel_required
def panel_pista_crear(request):
    urb, _ = resolver_urbanizacion(request)
    if request.method == 'POST' and urb:
        form = PistaForm(request.POST, urbanizacion=urb)
        if form.is_valid():
            try:
                pista = form.save()
                messages.success(request, f'Pista "{pista.nombre}" creada.')
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
        else:
            for errores in form.errors.values():
                for error in errores:
                    messages.error(request, error)
    return redirect(request.META.get('HTTP_REFERER') or 'panel:pistas')


@panel_required
def panel_pista_toggle(request, pk):
    pista = get_object_or_404(limitar_a_urbanizacion(request, Pista.objects.all()), pk=pk)
    if request.method == 'POST':
        pista.activa = not pista.activa
        pista.save()
        estado = 'activada' if pista.activa else 'desactivada'
        messages.success(request, f'Pista "{pista.nombre}" {estado}.')
    return redirect(request.META.get('HTTP_REFERER') or 'panel:pistas')


@panel_required
def panel_pista_eliminar(request, pk):
    pista = get_object_or_404(limitar_a_urbanizacion(request, Pista.objects.all()), pk=pk)
    if request.method == 'POST':
        if pista.reservas.exists():
            messages.error(
                request,
                f'No se puede eliminar "{pista.nombre}": tiene reservas asociadas. '
                f'Desactívala en su lugar para que no se pueda seguir reservando.',
            )
        else:
            nombre = pista.nombre
            pista.delete()
            messages.success(request, f'Pista "{nombre}" eliminada.')
    return redirect(request.META.get('HTTP_REFERER') or 'panel:pistas')
