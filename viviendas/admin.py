from django.contrib import admin
from .models import Portal, Vivienda


class ViviendaInline(admin.TabularInline):
    model = Vivienda
    extra = 1


@admin.register(Portal)
class PortalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'urbanizacion')
    list_filter = ('urbanizacion',)
    search_fields = ('nombre',)
    inlines = [ViviendaInline]


@admin.register(Vivienda)
class ViviendaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'portal', 'piso', 'puerta')
    list_filter = ('portal__urbanizacion', 'portal')
    search_fields = ('piso', 'puerta', 'portal__nombre')
