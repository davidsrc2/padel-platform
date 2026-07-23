from django.contrib import admin
from .models import Urbanizacion


@admin.register(Urbanizacion)
class UrbanizacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'num_pistas', 'hora_apertura', 'hora_cierre', 'max_reservas_por_vivienda')
    search_fields = ('nombre', 'direccion')
