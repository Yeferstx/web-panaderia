from django.db import transaction

from core.actividad import registrar_actividad
from core.templatetags.formato import pesos
from inventario.models import MovimientoInventario
from inventario.servicios import registrar_movimiento


@transaction.atomic
def crear_producto(formulario, usuario):
    producto = formulario.save()
    existencia_inicial = formulario.cleaned_data.get("existencia_inicial")

    if producto.lleva_existencias and existencia_inicial:
        registrar_movimiento(
            producto, MovimientoInventario.TIPO_INICIAL, existencia_inicial, "Existencia inicial", usuario
        )

    registrar_actividad(usuario, "Producto creado", f"{producto.nombre} con precio {texto_precio(producto)}")
    return producto


@transaction.atomic
def guardar_cambios_producto(formulario, usuario):
    precio_anterior = formulario.initial.get("precio_venta")
    producto = formulario.save()

    if precio_anterior != producto.precio_venta:
        registrar_actividad(
            usuario,
            "Cambio de precio",
            f"{producto.nombre}: de {pesos(precio_anterior) or 'sin precio'} a {texto_precio(producto)}",
        )
    return producto


@transaction.atomic
def cambiar_estado_producto(producto, usuario):
    producto.activo = not producto.activo
    producto.save(update_fields=["activo", "actualizado_en"])
    accion = "Producto activado" if producto.activo else "Producto desactivado"
    registrar_actividad(usuario, accion, producto.nombre)
    return producto


@transaction.atomic
def cambiar_estado_categoria(categoria, usuario):
    categoria.activa = not categoria.activa
    categoria.save(update_fields=["activa", "actualizado_en"])
    accion = "Categoría activada" if categoria.activa else "Categoría desactivada"
    registrar_actividad(usuario, accion, categoria.nombre)
    return categoria


def texto_precio(producto):
    if producto.forma_venta == producto.FORMA_IMPORTE:
        return "por importe"
    return pesos(producto.precio_venta)
