from datetime import date

from django.shortcuts import render
from django.utils import timezone

from usuarios.permisos import solo_administrador

from . import servicios


def leer_fecha(texto):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        return timezone.localdate()


@solo_administrador
def informe(request):
    tipo = request.GET.get("tipo", "diario")
    if tipo not in servicios.NOMBRES_TIPO:
        tipo = "diario"
    fecha = leer_fecha(request.GET.get("fecha"))

    datos = servicios.armar_informe(tipo, fecha)
    datos["fecha"] = fecha
    datos["anterior"] = servicios.fecha_anterior(tipo, fecha)
    datos["siguiente"] = servicios.fecha_siguiente(tipo, fecha)
    datos["hay_siguiente"] = datos["siguiente"] <= timezone.localdate()
    datos["tipos"] = servicios.NOMBRES_TIPO
    return render(request, "reportes/informe.html", datos)
