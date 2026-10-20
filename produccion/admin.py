from django.contrib import admin

from .models import ConsumoPreparacion, Preparacion


class ConsumoEnLinea(admin.TabularInline):
    model = ConsumoPreparacion
    extra = 0
    can_delete = False
    readonly_fields = ["insumo", "cantidad"]


@admin.register(Preparacion)
class PreparacionAdmin(admin.ModelAdmin):
    list_display = ["fecha", "nombre", "bandejas", "unidades_aproximadas", "estado", "usuario"]
    list_filter = ["estado"]
    inlines = [ConsumoEnLinea]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
