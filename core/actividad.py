from .models import RegistroActividad


def registrar_actividad(usuario, accion, descripcion):
    return RegistroActividad.objects.create(
        usuario=usuario,
        accion=accion,
        descripcion=descripcion,
    )
