from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.actividad import registrar_actividad
from core.templatetags.formato import pesos
from inventario.models import Insumo, MovimientoInventario
from inventario.servicios import registrar_movimiento
from productos.models import Producto

from .models import Compra, DetalleCompra


def preparar_detalle(linea):
    articulo = linea["articulo"]
    cantidad = linea["cantidad"]
    valor = linea["valor"]
    costo_unitario = (valor / cantidad).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    detalle = DetalleCompra(cantidad=cantidad, subtotal=valor, costo_unitario=costo_unitario)

    if articulo == "otro":
        detalle.tipo = DetalleCompra.TIPO_OTRO
        detalle.descripcion = linea["descripcion"].strip()
        return detalle

    tipo, _, identificador = articulo.partition("-")
    if tipo == "producto":
        producto = Producto.objects.filter(
            pk=identificador, activo=True, control_inventario=Producto.CONTROL_UNIDADES
        ).first()
        if producto is None:
            raise ValidationError("Uno de los productos ya no está disponible para compras.")
        detalle.tipo = DetalleCompra.TIPO_REVENTA
        detalle.producto = producto
        detalle.descripcion = producto.nombre
        detalle.unidad_medida = producto.unidad_medida
    elif tipo == "insumo":
        insumo = Insumo.objects.filter(pk=identificador, activo=True).first()
        if insumo is None:
            raise ValidationError("Uno de los insumos ya no está disponible.")
        detalle.tipo = DetalleCompra.TIPO_INSUMO
        detalle.insumo = insumo
        detalle.descripcion = insumo.nombre
        detalle.unidad_medida = insumo.unidad_medida
    else:
        raise ValidationError("Uno de los artículos no es válido.")
    return detalle


def registrar_compra(usuario, datos, lineas, codigo_operacion):
    existente = Compra.objects.filter(codigo_operacion=codigo_operacion).first()
    if existente:
        return existente, True

    detalles = [preparar_detalle(linea) for linea in lineas]
    if not detalles:
        raise ValidationError("Agregue al menos un artículo a la compra.")

    pagada = datos["estado_pago"] == Compra.PAGO_PAGADA
    try:
        with transaction.atomic():
            compra = Compra.objects.create(
                fecha=datos["fecha"],
                proveedor=datos.get("proveedor"),
                usuario=usuario,
                total=sum(detalle.subtotal for detalle in detalles),
                estado_pago=datos["estado_pago"],
                metodo_pago=datos["metodo_pago"] if pagada else "",
                fecha_pago=datos["fecha"] if pagada else None,
                observaciones=datos.get("observaciones", "").strip(),
                codigo_operacion=codigo_operacion,
            )
            for detalle in detalles:
                detalle.compra = compra
                detalle.save()
                articulo = detalle.producto or detalle.insumo
                if articulo:
                    registrar_movimiento(
                        articulo,
                        MovimientoInventario.TIPO_ENTRADA,
                        detalle.cantidad,
                        f"Compra #{compra.pk}",
                        usuario,
                        origen="compra",
                        origen_id=compra.pk,
                    )
    except IntegrityError:
        existente = Compra.objects.filter(codigo_operacion=codigo_operacion).first()
        if existente:
            return existente, True
        raise

    return compra, False


@transaction.atomic
def registrar_pago(compra, metodo_pago, fecha_pago, usuario):
    compra = Compra.objects.select_for_update().get(pk=compra.pk)
    if compra.esta_anulada:
        raise ValidationError("No se puede pagar una compra anulada.")
    if not compra.esta_pendiente:
        raise ValidationError("Esta compra ya estaba pagada.")
    if fecha_pago < compra.fecha:
        raise ValidationError("La fecha de pago no puede ser anterior a la fecha de la compra.")
    if fecha_pago > timezone.localdate():
        raise ValidationError("La fecha de pago no puede ser futura.")

    compra.estado_pago = Compra.PAGO_PAGADA
    compra.metodo_pago = metodo_pago
    compra.fecha_pago = fecha_pago
    compra.save(update_fields=["estado_pago", "metodo_pago", "fecha_pago"])
    registrar_actividad(usuario, "Compra pagada", f"Compra #{compra.pk} por {pesos(compra.total)}")
    return compra


@transaction.atomic
def anular_compra(compra, usuario, motivo):
    compra = Compra.objects.select_for_update().get(pk=compra.pk)
    motivo = motivo.strip()
    if compra.esta_anulada:
        raise ValidationError("Esta compra ya estaba anulada.")
    if not motivo:
        raise ValidationError("Escriba el motivo de la anulación.")

    entradas = MovimientoInventario.objects.filter(
        origen="compra", origen_id=compra.pk, tipo=MovimientoInventario.TIPO_ENTRADA
    ).select_related("producto", "insumo")
    for entrada in entradas:
        registrar_movimiento(
            entrada.articulo,
            MovimientoInventario.TIPO_ANULACION,
            -entrada.cantidad,
            f"Anulación de la compra #{compra.pk}",
            usuario,
            origen="compra",
            origen_id=compra.pk,
        )

    compra.estado = Compra.ESTADO_ANULADA
    compra.anulada_por = usuario
    compra.fecha_anulacion = timezone.now()
    compra.motivo_anulacion = motivo[:255]
    compra.save(update_fields=["estado", "anulada_por", "fecha_anulacion", "motivo_anulacion"])
    registrar_actividad(usuario, "Compra anulada", f"Compra #{compra.pk} por {pesos(compra.total)}. Motivo: {motivo}")
    return compra
