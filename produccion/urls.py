from django.urls import path

from . import views

app_name = "produccion"

urlpatterns = [
    path("", views.lista_produccion, name="lista"),
    path("nueva/", views.nueva_preparacion, name="nueva"),
    path("<int:pk>/", views.detalle_preparacion, name="detalle"),
    path("<int:pk>/anular/", views.anular_preparacion, name="anular"),
]
