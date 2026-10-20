from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.actividad import registrar_actividad
from core.templatetags.formato import cantidad as formato_cantidad
from inventario.models import MovimientoInventario
from inventario.servicios import registrar_movimiento

from .models import ConsumoPreparacion, Preparacion


def unir_consumos(consumos):
    totales = {}
    for consumo in consumos:
        insumo = consumo["insumo"]
        totales[insumo] = totales.get(insumo, 0) + consumo["cantidad"]
    return totales


def registrar_preparacion(usuario, datos, consumos, codigo_operacion):
    existente = Preparacion.objects.filter(codigo_operacion=codigo_operacion).first()
    if existente:
        return existente, [], True

    advertencias = []
    try:
        with transaction.atomic():
            preparacion = Preparacion.objects.create(
                usuario=usuario,
                codigo_operacion=codigo_operacion,
                fecha=datos["fecha"],
                nombre=datos["nombre"].strip(),
                producto=datos.get("producto"),
                bandejas=datos.get("bandejas"),
                unidades_aproximadas=datos.get("unidades_aproximadas"),
                unidades_minimas=datos.get("unidades_minimas"),
                unidades_maximas=datos.get("unidades_maximas"),
                observaciones=datos.get("observaciones", "").strip(),
            )
            for insumo, cantidad in unir_consumos(consumos).items():
                if not insumo.activo:
                    raise ValidationError(f"El insumo «{insumo.nombre}» está inactivo.")
                ConsumoPreparacion.objects.create(preparacion=preparacion, insumo=insumo, cantidad=cantidad)
                movimiento = registrar_movimiento(
                    insumo,
                    MovimientoInventario.TIPO_SALIDA,
                    -cantidad,
                    f"Producción: {preparacion.nombre}",
                    usuario,
                    origen="produccion",
                    origen_id=preparacion.pk,
                )
                if movimiento.existencia_resultante < 0:
                    advertencias.append(
                        f"«{insumo.nombre}» quedó en {formato_cantidad(movimiento.existencia_resultante)} "
                        f"{insumo.unidad_medida} en el sistema. Revise el inventario."
                    )
    except IntegrityError:
        existente = Preparacion.objects.filter(codigo_operacion=codigo_operacion).first()
        if existente:
            return existente, [], True
        raise

    return preparacion, advertencias, False


@transaction.atomic
def anular_preparacion(preparacion, usuario, motivo):
    preparacion = Preparacion.objects.select_for_update().get(pk=preparacion.pk)
    motivo = motivo.strip()
    if preparacion.esta_anulada:
        raise ValidationError("Esta preparación ya estaba anulada.")
    if not motivo:
        raise ValidationError("Escriba el motivo de la anulación.")

    salidas = MovimientoInventario.objects.filter(
        origen="produccion", origen_id=preparacion.pk, tipo=MovimientoInventario.TIPO_SALIDA
    ).select_related("insumo")
    for salida in salidas:
        registrar_movimiento(
            salida.insumo,
            MovimientoInventario.TIPO_ANULACION,
            -salida.cantidad,
            f"Anulación de producción: {preparacion.nombre}",
            usuario,
            origen="produccion",
            origen_id=preparacion.pk,
        )

    preparacion.estado = Preparacion.ESTADO_ANULADA
    preparacion.anulada_por = usuario
    preparacion.fecha_anulacion = timezone.now()
    preparacion.motivo_anulacion = motivo[:255]
    preparacion.save(update_fields=["estado", "anulada_por", "fecha_anulacion", "motivo_anulacion"])
    registrar_actividad(usuario, "Producción anulada", f"{preparacion}. Motivo: {motivo}")
    return preparacion
