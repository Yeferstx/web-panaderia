from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("productos/", include("productos.urls")),
    path("inventario/", include("inventario.urls")),
    path("ventas/", include("ventas.urls")),
    path("compras/", include("compras.urls")),
    path("gastos/", include("gastos.urls")),
    path("produccion/", include("produccion.urls")),
    path("informes/", include("reportes.urls")),
    path("", include("usuarios.urls")),
    path("", include("core.urls")),
]
