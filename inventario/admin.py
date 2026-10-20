from django.contrib import admin

from .models import Insumo, MovimientoInventario


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "unidad_medida", "existencia", "existencia_minima", "activo"]
    readonly_fields = ["existencia"]


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ["fecha", "tipo", "producto", "insumo", "cantidad", "existencia_resultante", "usuario"]
    list_filter = ["tipo"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
