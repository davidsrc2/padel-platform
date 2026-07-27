from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .emails import enviar_aprobacion_usuario
from .models import Usuario

admin.site.site_header = 'Pádel — Administración'
admin.site.site_title = 'Pádel Admin'
admin.site.index_title = 'Panel de gestión'


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'get_full_name', 'rol', 'vivienda', 'aprobado', 'is_active')
    list_filter = ('rol', 'aprobado', 'vivienda__portal__urbanizacion')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    actions = ['aprobar_usuarios']

    fieldsets = UserAdmin.fieldsets + (
        ('Datos de la urbanización', {'fields': ('vivienda', 'rol', 'aprobado', 'telefono')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos de la urbanización', {'fields': ('vivienda', 'rol', 'aprobado', 'telefono')}),
    )

    @admin.action(description='Aprobar usuarios seleccionados')
    def aprobar_usuarios(self, request, queryset):
        for usuario in queryset.filter(aprobado=False):
            usuario.aprobado = True
            usuario.save()
            enviar_aprobacion_usuario(usuario)
