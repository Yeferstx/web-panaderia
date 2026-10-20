from django.contrib import admin

from .models import DetalleVenta, Venta


class DetalleVentaEnLinea(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    can_delete = False
    readonly_fields = ["producto", "nombre_producto", "cantidad", "precio_unitario", "subtotal"]


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ["id", "fecha", "usuario", "total", "metodo_pago", "estado"]
    list_filter = ["estado", "metodo_pago"]
    inlines = [DetalleVentaEnLinea]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
