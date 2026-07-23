from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import RegistroForm
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
