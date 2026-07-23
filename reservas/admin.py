from django.contrib import admin
from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('pista', 'usuario', 'fecha', 'hora_inicio', 'hora_fin', 'estado')
    list_filter = ('estado', 'pista__urbanizacion', 'fecha')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    date_hierarchy = 'fecha'
    actions = ['cancelar_reservas']

    @admin.action(description='Cancelar reservas seleccionadas')
    def cancelar_reservas(self, request, queryset):
        queryset.update(estado=Reserva.ESTADO_CANCELADA)
