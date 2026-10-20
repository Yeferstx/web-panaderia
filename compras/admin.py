from django.contrib import admin

from .models import Compra, DetalleCompra, Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ["nombre", "telefono", "activo"]


class DetalleCompraEnLinea(admin.TabularInline):
    model = DetalleCompra
    extra = 0
    can_delete = False
    readonly_fields = ["tipo", "producto", "insumo", "descripcion", "cantidad", "unidad_medida", "costo_unitario", "subtotal"]


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ["id", "fecha", "proveedor", "total", "estado_pago", "estado"]
    list_filter = ["estado", "estado_pago"]
    inlines = [DetalleCompraEnLinea]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
