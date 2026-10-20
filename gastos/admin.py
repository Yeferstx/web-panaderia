from django.contrib import admin

from .models import CategoriaGasto, CierreCaja, Gasto, MovimientoCaja


@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activa"]


class SoloLecturaAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Gasto)
class GastoAdmin(SoloLecturaAdmin):
    list_display = ["fecha", "categoria", "descripcion", "valor", "metodo_pago", "estado"]
    list_filter = ["estado", "categoria"]


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(SoloLecturaAdmin):
    list_display = ["fecha", "tipo", "valor", "motivo", "usuario"]


@admin.register(CierreCaja)
class CierreCajaAdmin(SoloLecturaAdmin):
    list_display = ["fecha", "efectivo_esperado", "efectivo_contado", "diferencia", "usuario"]
