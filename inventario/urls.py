from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.panel_inventario, name="panel"),
    path("insumos/nuevo/", views.crear_insumo, name="insumo_nuevo"),
    path("insumos/<int:pk>/editar/", views.editar_insumo, name="insumo_editar"),
    path("insumos/<int:pk>/estado/", views.cambiar_estado_insumo, name="insumo_estado"),
    path("ajustar/producto/<int:pk>/", views.ajustar_producto, name="ajustar_producto"),
    path("ajustar/insumo/<int:pk>/", views.ajustar_insumo, name="ajustar_insumo"),
    path("movimientos/", views.lista_movimientos, name="movimientos"),
]
