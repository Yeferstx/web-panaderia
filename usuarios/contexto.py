from django.conf import settings

from .permisos import es_administrador


def datos_usuario(request):
    return {
        "es_administrador": es_administrador(request.user),
        "nombre_negocio": settings.NOMBRE_NEGOCIO,
        "version_estilos": settings.VERSION_ESTILOS,
    }
