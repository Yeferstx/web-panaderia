from django.urls import path

from . import views

app_name = "gastos"

urlpatterns = [
    path("", views.lista_gastos, name="lista"),
    path("nuevo/", views.nuevo_gasto, name="nuevo"),
    path("<int:pk>/", views.detalle_gasto, name="detalle"),
    path("<int:pk>/anular/", views.anular_gasto, name="anular"),
    path("categorias/", views.categorias_gasto, name="categorias"),
    path("categorias/<int:pk>/estado/", views.cambiar_estado_categoria, name="categoria_estado"),
    path("caja/", views.caja, name="caja"),
    path("caja/cerrar/", views.cerrar_caja, name="cerrar_caja"),
    path("caja/movimiento/", views.nuevo_movimiento_caja, name="movimiento_caja"),
]
