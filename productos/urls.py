from django.urls import path

from . import views

app_name = "productos"

urlpatterns = [
    path("", views.lista_productos, name="lista"),
    path("nuevo/", views.crear_producto, name="nuevo"),
    path("<int:pk>/editar/", views.editar_producto, name="editar"),
    path("<int:pk>/estado/", views.cambiar_estado_producto, name="estado"),
    path("categorias/", views.lista_categorias, name="categorias"),
    path("categorias/nueva/", views.crear_categoria, name="categoria_nueva"),
    path("categorias/<int:pk>/editar/", views.editar_categoria, name="categoria_editar"),
    path("categorias/<int:pk>/estado/", views.cambiar_estado_categoria, name="categoria_estado"),
]
