from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from panel.permisos import panel_required, resolver_urbanizacion
from .forms import UrbanizacionForm


@panel_required
def panel_urbanizacion(request):
    urb, urbanizaciones = resolver_urbanizacion(request)
    if not urb:
        messages.error(request, 'No hay ninguna urbanización creada todavía.')
        return redirect('panel:inicio')

    if request.method == 'POST':
        form = UrbanizacionForm(request.POST, instance=urb)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Ajustes de la urbanización guardados.')
                return redirect(request.get_full_path())
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
        else:
            for errores in form.errors.values():
                for error in errores:
                    messages.error(request, error)
    else:
        form = UrbanizacionForm(instance=urb)

    return render(request, 'panel/urbanizacion.html', {
        'form': form, 'urb': urb, 'urbanizaciones': urbanizaciones,
    })
