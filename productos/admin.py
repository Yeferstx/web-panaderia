from django.contrib import admin

from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activa"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "categoria", "precio_venta", "forma_venta", "control_inventario", "existencia", "activo"]
    list_filter = ["categoria", "activo"]
    search_fields = ["nombre"]
    readonly_fields = ["existencia"]
