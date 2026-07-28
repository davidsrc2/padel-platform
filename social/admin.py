from django.contrib import admin

from .models import Seguimiento


@admin.register(Seguimiento)
class SeguimientoAdmin(admin.ModelAdmin):
    list_display = ('seguidor', 'seguido', 'creado')
    search_fields = ('seguidor__username', 'seguido__username')
