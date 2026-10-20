import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.actividad import registrar_actividad
from core.templatetags.formato import cantidad as formato_cantidad
from core.templatetags.formato import pesos
from inventario.models import MovimientoInventario
from inventario.servicios import registrar_movimiento
from productos.models import Producto

from .models import DetalleVenta, Venta


def leer_numero(texto, nombre_campo):
    try:
        numero = Decimal(str(texto).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"El valor de {nombre_campo} no es un número válido.")
    if not numero.is_finite():
        raise ValidationError(f"El valor de {nombre_campo} no es un número válido.")
    return numero


def leer_lineas(texto_json):
    try:
        lineas = json.loads(texto_json or "[]")
    except json.JSONDecodeError:
        raise ValidationError("No se pudo leer la venta. Vuelva a agregar los productos.")

    if not isinstance(lineas, list) or not lineas:
        raise ValidationError("Agregue al menos un producto a la venta.")
    return lineas


def preparar_detalles(lineas):
    detalles = []
    ids = [linea.get("producto") for linea in lineas if isinstance(linea, dict)]
    productos = Producto.objects.in_bulk(ids)

    for linea in lineas:
        if not isinstance(linea, dict):
            raise ValidationError("No se pudo leer la venta. Vuelva a agregar los productos.")

        producto = productos.get(linea.get("producto"))
        if producto is None or not producto.activo:
            raise ValidationError("Uno de los productos ya no está disponible. Quítelo y vuelva a intentar.")

        if producto.forma_venta == Producto.FORMA_IMPORTE:
            importe = leer_numero(linea.get("importe"), f"«{producto.nombre}»")
            if importe <= 0 or importe != importe.to_integral_value():
                raise ValidationError(f"El valor de «{producto.nombre}» debe ser un número entero mayor que cero.")
            detalles.append(DetalleVenta(
                producto=producto,
                nombre_producto=producto.nombre,
                subtotal=importe,
            ))
        else:
            cantidad = leer_numero(linea.get("cantidad"), f"cantidad de «{producto.nombre}»")
            if cantidad <= 0:
                raise ValidationError(f"La cantidad de «{producto.nombre}» debe ser mayor que cero.")
            if producto.unidad_medida == "und" and cantidad != cantidad.to_integral_value():
                raise ValidationError(f"«{producto.nombre}» se vende por unidades enteras.")
            if cantidad.as_tuple().exponent < -3:
                raise ValidationError(f"La cantidad de «{producto.nombre}» tiene demasiados decimales.")

            subtotal = (cantidad * producto.precio_venta).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            if subtotal <= 0:
                raise ValidationError(f"La cantidad de «{producto.nombre}» es demasiado pequeña.")
            detalles.append(DetalleVenta(
                producto=producto,
                nombre_producto=producto.nombre,
                cantidad=cantidad,
                precio_unitario=producto.precio_venta,
                subtotal=subtotal,
            ))
    return detalles


def registrar_venta(usuario, texto_lineas, metodo_pago, observaciones, codigo_operacion):
    venta_existente = Venta.objects.filter(codigo_operacion=codigo_operacion).first()
    if venta_existente:
        return venta_existente, [], True

    metodos_validos = [opcion[0] for opcion in Venta.METODOS_PAGO]
    if metodo_pago not in metodos_validos:
        raise ValidationError("Elija el método de pago.")

    detalles = preparar_detalles(leer_lineas(texto_lineas))
    total = sum(detalle.subtotal for detalle in detalles)

    try:
        with transaction.atomic():
            venta = Venta.objects.create(
                usuario=usuario,
                total=total,
                metodo_pago=metodo_pago,
                observaciones=observaciones.strip()[:255],
                codigo_operacion=codigo_operacion,
            )
            advertencias = []
            for detalle in detalles:
                detalle.venta = venta
                detalle.save()

                producto = detalle.producto
                if producto.lleva_existencias:
                    movimiento = registrar_movimiento(
                        producto,
                        MovimientoInventario.TIPO_SALIDA,
                        -detalle.cantidad,
                        f"Venta #{venta.pk}",
                        usuario,
                        origen="venta",
                        origen_id=venta.pk,
                    )
                    if movimiento.existencia_resultante < 0:
                        advertencias.append(
                            f"«{producto.nombre}» quedó en {formato_cantidad(movimiento.existencia_resultante)} "
                            "en el sistema. Revise el inventario y haga un ajuste si el conteo no coincide."
                        )
    except IntegrityError:
        venta_existente = Venta.objects.filter(codigo_operacion=codigo_operacion).first()
        if venta_existente:
            return venta_existente, [], True
        raise

    return venta, advertencias, False


@transaction.atomic
def anular_venta(venta, usuario, motivo):
    venta = Venta.objects.select_for_update().get(pk=venta.pk)
    motivo = motivo.strip()

    if venta.esta_anulada:
        raise ValidationError("Esta venta ya estaba anulada.")
    if not motivo:
        raise ValidationError("Escriba el motivo de la anulación.")

    movimientos = MovimientoInventario.objects.filter(
        origen="venta", origen_id=venta.pk, tipo=MovimientoInventario.TIPO_SALIDA
    ).select_related("producto")
    for movimiento in movimientos:
        registrar_movimiento(
            movimiento.producto,
            MovimientoInventario.TIPO_ANULACION,
            -movimiento.cantidad,
            f"Anulación de la venta #{venta.pk}",
            usuario,
            origen="venta",
            origen_id=venta.pk,
        )

    venta.estado = Venta.ESTADO_ANULADA
    venta.anulada_por = usuario
    venta.fecha_anulacion = timezone.now()
    venta.motivo_anulacion = motivo[:255]
    venta.save(update_fields=["estado", "anulada_por", "fecha_anulacion", "motivo_anulacion"])

    registrar_actividad(usuario, "Venta anulada", f"Venta #{venta.pk} por {pesos(venta.total)}. Motivo: {motivo}")
    return venta
