from django.contrib import admin
from .models import Pista


@admin.register(Pista)
class PistaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'urbanizacion', 'activa')
    list_filter = ('urbanizacion', 'activa')
    search_fields = ('nombre',)
