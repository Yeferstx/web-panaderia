from django.urls import path

from . import views

app_name = "compras"

urlpatterns = [
    path("", views.lista_compras, name="lista"),
    path("nueva/", views.nueva_compra, name="nueva"),
    path("<int:pk>/", views.detalle_compra, name="detalle"),
    path("<int:pk>/pagar/", views.pagar_compra, name="pagar"),
    path("<int:pk>/anular/", views.anular_compra, name="anular"),
    path("proveedores/", views.lista_proveedores, name="proveedores"),
    path("proveedores/nuevo/", views.crear_proveedor, name="proveedor_nuevo"),
    path("proveedores/<int:pk>/editar/", views.editar_proveedor, name="proveedor_editar"),
    path("proveedores/<int:pk>/estado/", views.cambiar_estado_proveedor, name="proveedor_estado"),
]
