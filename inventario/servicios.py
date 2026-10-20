from django.core.exceptions import ValidationError
from django.db import transaction

from core.actividad import registrar_actividad
from core.templatetags.formato import cantidad as formato_cantidad
from productos.models import Producto

from .models import Insumo, MovimientoInventario


def bloquear_articulo(articulo):
    modelo = type(articulo)
    return modelo.objects.select_for_update().get(pk=articulo.pk)


@transaction.atomic
def registrar_movimiento(articulo, tipo, cantidad, motivo, usuario, origen="", origen_id=None):
    if cantidad == 0:
        raise ValidationError("La cantidad del movimiento no puede ser cero.")

    if isinstance(articulo, Producto) and not articulo.lleva_existencias:
        raise ValidationError(f"«{articulo.nombre}» no lleva control de existencias por unidades.")

    articulo = bloquear_articulo(articulo)
    anterior = articulo.existencia
    articulo.existencia = anterior + cantidad
    articulo.save(update_fields=["existencia", "actualizado_en"])

    movimiento = MovimientoInventario(
        tipo=tipo,
        cantidad=cantidad,
        existencia_anterior=anterior,
        existencia_resultante=articulo.existencia,
        motivo=motivo,
        usuario=usuario,
        origen=origen,
        origen_id=origen_id,
    )
    if isinstance(articulo, Insumo):
        movimiento.insumo = articulo
    else:
        movimiento.producto = articulo
    movimiento.save()
    return movimiento


@transaction.atomic
def ajustar_existencia(articulo, existencia_contada, motivo, usuario):
    articulo = bloquear_articulo(articulo)
    diferencia = existencia_contada - articulo.existencia

    if diferencia == 0:
        raise ValidationError("La cantidad contada es igual a la registrada. No hay nada que ajustar.")

    movimiento = registrar_movimiento(
        articulo, MovimientoInventario.TIPO_AJUSTE, diferencia, motivo, usuario
    )
    registrar_actividad(
        usuario,
        "Ajuste de inventario",
        f"{articulo.nombre}: de {formato_cantidad(movimiento.existencia_anterior)} a "
        f"{formato_cantidad(movimiento.existencia_resultante)} {articulo.unidad_medida}. Motivo: {motivo}",
    )
    return movimiento


@transaction.atomic
def crear_insumo(formulario, usuario):
    insumo = formulario.save()
    inicial = formulario.cleaned_data.get("existencia_inicial")
    if inicial:
        registrar_movimiento(insumo, MovimientoInventario.TIPO_INICIAL, inicial, "Existencia inicial", usuario)
    registrar_actividad(usuario, "Insumo creado", str(insumo))
    return insumo


@transaction.atomic
def cambiar_estado_insumo(insumo, usuario):
    insumo.activo = not insumo.activo
    insumo.save(update_fields=["activo", "actualizado_en"])
    accion = "Insumo activado" if insumo.activo else "Insumo desactivado"
    registrar_actividad(usuario, accion, insumo.nombre)
    return insumo


def productos_con_existencias():
    return Producto.objects.filter(
        activo=True, control_inventario=Producto.CONTROL_UNIDADES
    ).select_related("categoria")


def articulos_con_alerta():
    productos = [p for p in productos_con_existencias() if p.estado_existencia != "normal"]
    insumos = [i for i in Insumo.objects.filter(activo=True) if i.estado_existencia != "normal"]
    return productos, insumos
