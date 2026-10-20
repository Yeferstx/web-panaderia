from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from compras.models import Compra
from core.actividad import registrar_actividad
from core.opciones import EFECTIVO
from core.templatetags.formato import pesos
from ventas.models import Venta

from .models import CierreCaja, Gasto, MovimientoCaja


def sumar(consulta, campo):
    return consulta.aggregate(total=Sum(campo))["total"] or 0


def registrar_gasto(usuario, datos, codigo_operacion):
    existente = Gasto.objects.filter(codigo_operacion=codigo_operacion).first()
    if existente:
        return existente, True
    try:
        with transaction.atomic():
            gasto = Gasto.objects.create(usuario=usuario, codigo_operacion=codigo_operacion, **datos)
    except IntegrityError:
        existente = Gasto.objects.filter(codigo_operacion=codigo_operacion).first()
        if existente:
            return existente, True
        raise
    return gasto, False


@transaction.atomic
def anular_gasto(gasto, usuario, motivo):
    gasto = Gasto.objects.select_for_update().get(pk=gasto.pk)
    motivo = motivo.strip()
    if gasto.esta_anulado:
        raise ValidationError("Este gasto ya estaba anulado.")
    if not motivo:
        raise ValidationError("Escriba el motivo de la anulación.")

    gasto.estado = Gasto.ESTADO_ANULADO
    gasto.anulado_por = usuario
    gasto.fecha_anulacion = timezone.now()
    gasto.motivo_anulacion = motivo[:255]
    gasto.save(update_fields=["estado", "anulado_por", "fecha_anulacion", "motivo_anulacion"])
    registrar_actividad(usuario, "Gasto anulado", f"{gasto.descripcion} por {pesos(gasto.valor)}. Motivo: {motivo}")
    return gasto


def saldo_inicial_sugerido(fecha):
    cierre_anterior = CierreCaja.objects.filter(fecha__lt=fecha).order_by("-fecha").first()
    if cierre_anterior:
        return cierre_anterior.efectivo_contado
    return 0


def calcular_caja(fecha, saldo_inicial):
    ventas = Venta.objects.filter(estado=Venta.ESTADO_CONFIRMADA, fecha__date=fecha)
    gastos = Gasto.objects.filter(estado=Gasto.ESTADO_CONFIRMADO, fecha=fecha)
    compras_pagadas = Compra.objects.filter(
        estado=Compra.ESTADO_CONFIRMADA, estado_pago=Compra.PAGO_PAGADA, fecha_pago=fecha
    )
    movimientos = MovimientoCaja.objects.filter(fecha=fecha)

    resumen = {
        "saldo_inicial": saldo_inicial,
        "ventas_efectivo": sumar(ventas.filter(metodo_pago=EFECTIVO), "total"),
        "ventas_otros_medios": sumar(ventas.exclude(metodo_pago=EFECTIVO), "total"),
        "gastos_efectivo": sumar(gastos.filter(metodo_pago=EFECTIVO), "valor"),
        "gastos_otros_medios": sumar(gastos.exclude(metodo_pago=EFECTIVO), "valor"),
        "compras_efectivo": sumar(compras_pagadas.filter(metodo_pago=EFECTIVO), "total"),
        "compras_otros_medios": sumar(compras_pagadas.exclude(metodo_pago=EFECTIVO), "total"),
        "entradas": sumar(movimientos.filter(tipo=MovimientoCaja.TIPO_INGRESO), "valor"),
        "salidas": sumar(movimientos.filter(tipo=MovimientoCaja.TIPO_RETIRO), "valor"),
    }
    resumen["efectivo_esperado"] = (
        resumen["saldo_inicial"]
        + resumen["ventas_efectivo"]
        + resumen["entradas"]
        - resumen["gastos_efectivo"]
        - resumen["compras_efectivo"]
        - resumen["salidas"]
    )
    return resumen


@transaction.atomic
def cerrar_caja(fecha, saldo_inicial, efectivo_contado, observaciones, usuario):
    if fecha > timezone.localdate():
        raise ValidationError("No se puede cerrar la caja de un día futuro.")
    if CierreCaja.objects.select_for_update().filter(fecha=fecha).exists():
        raise ValidationError("La caja de ese día ya está cerrada.")

    resumen = calcular_caja(fecha, saldo_inicial)
    try:
        with transaction.atomic():
            cierre = CierreCaja.objects.create(
                fecha=fecha,
                saldo_inicial=saldo_inicial,
                ventas_efectivo=resumen["ventas_efectivo"],
                gastos_efectivo=resumen["gastos_efectivo"],
                compras_efectivo=resumen["compras_efectivo"],
                entradas=resumen["entradas"],
                salidas=resumen["salidas"],
                efectivo_esperado=resumen["efectivo_esperado"],
                efectivo_contado=efectivo_contado,
                diferencia=efectivo_contado - resumen["efectivo_esperado"],
                usuario=usuario,
                observaciones=observaciones.strip(),
            )
    except IntegrityError:
        raise ValidationError("La caja de ese día ya está cerrada.")

    registrar_actividad(
        usuario,
        "Cierre de caja",
        f"{fecha:%d/%m/%Y}: esperado {pesos(cierre.efectivo_esperado)}, contado {pesos(cierre.efectivo_contado)}, "
        f"diferencia {pesos(cierre.diferencia)}",
    )
    return cierre
