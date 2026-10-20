from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

GRUPO_ADMINISTRADOR = "Administrador"
GRUPO_EMPLEADO = "Empleado"


def es_administrador(usuario):
    if not usuario.is_authenticated:
        return False
    if usuario.is_superuser:
        return True
    return usuario.groups.filter(name=GRUPO_ADMINISTRADOR).exists()


def solo_administrador(vista):
    @wraps(vista)
    @login_required
    def vista_protegida(request, *args, **kwargs):
        if not es_administrador(request.user):
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return vista_protegida
