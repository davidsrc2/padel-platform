from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from urbanizaciones.models import Urbanizacion


def panel_required(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        usuario = request.user
        if not usuario.is_authenticated:
            return redirect('accounts:login')
        if usuario.rol not in (usuario.ROL_ADMIN_URB, usuario.ROL_SUPERADMIN):
            messages.error(request, 'No tienes permiso para acceder al panel de gestión.')
            return redirect('reservas:calendario')
        return vista(request, *args, **kwargs)
    return envoltura


def resolver_urbanizacion(request):
    """
    Devuelve (urbanizacion, lista_para_selector) según el rol:
    - admin_urb: siempre la suya, sin selector.
    - superadmin: la elegida por ?urbanizacion=<id> en la query, o la primera
      disponible; con la lista completa para mostrar un selector.
    """
    usuario = request.user

    if usuario.rol == usuario.ROL_ADMIN_URB:
        return usuario.urbanizacion, None

    urbanizaciones = Urbanizacion.objects.order_by('nombre')
    urb_id = request.GET.get('urbanizacion')
    urb = urbanizaciones.filter(pk=urb_id).first() if urb_id else urbanizaciones.first()
    return urb, urbanizaciones


def limitar_a_urbanizacion(request, queryset, campo='urbanizacion'):
    """
    Si el usuario es admin_urb, restringe el queryset a su propia urbanización
    (evita que edite o vea datos de otra comunidad). Superadmin no se restringe.
    """
    usuario = request.user
    if usuario.rol == usuario.ROL_ADMIN_URB:
        return queryset.filter(**{campo: usuario.urbanizacion})
    return queryset
