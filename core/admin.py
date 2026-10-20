from django.contrib import admin

from .models import RegistroActividad


@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    list_display = ["fecha", "usuario", "accion", "descripcion"]
    list_filter = ["accion"]
