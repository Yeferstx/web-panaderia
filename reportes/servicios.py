import calendar
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Max, Sum
from django.db.models.functions import TruncDate

from compras.models import Compra, DetalleCompra
from core.opciones import METODOS_PAGO
from gastos.models import Gasto, MovimientoCaja
from inventario.models import Insumo, MovimientoInventario
from produccion.models import ConsumoPreparacion, Preparacion
from productos.models import Producto
from ventas.models import DetalleVenta, Venta

NOMBRES_TIPO = {
    "diario": "Informe diario",
    "semanal": "Informe semanal",
    "mensual": "Informe mensual",
}


def sumar(consulta, campo):
    return consulta.aggregate(total=Sum(campo))["total"] or 0


def calcular_rango(tipo, fecha):
    if tipo == "semanal":
        lunes = fecha - timedelta(days=fecha.weekday())
        return lunes, lunes + timedelta(days=6)
    if tipo == "mensual":
        ultimo_dia = calendar.monthrange(fecha.year, fecha.month)[1]
        return fecha.replace(day=1), fecha.replace(day=ultimo_dia)
    return fecha, fecha


def fecha_anterior(tipo, fecha):
    desde, _ = calcular_rango(tipo, fecha)
    if tipo == "semanal":
        return desde - timedelta(days=7)
    if tipo == "mensual":
        return desde - timedelta(days=1)
    return fecha - timedelta(days=1)


def fecha_siguiente(tipo, fecha):
    _, hasta = calcular_rango(tipo, fecha)
    if tipo == "diario":
        return fecha + timedelta(days=1)
    return hasta + timedelta(days=1)


def ventas_del_periodo(desde, hasta):
    return Venta.objects.filter(
        estado=Venta.ESTADO_CONFIRMADA, fecha__date__gte=desde, fecha__date__lte=hasta
    )


def resumen_ventas(desde, hasta):
    ventas = ventas_del_periodo(desde, hasta)
    total = sumar(ventas, "total")
    cantidad = ventas.count()

    por_metodo = []
    for valor, nombre in METODOS_PAGO:
        por_metodo.append({"nombre": nombre, "total": sumar(ventas.filter(metodo_pago=valor), "total")})

    return {
        "total": total,
        "cantidad": cantidad,
        "promedio": round(total / cantidad) if cantidad else 0,
        "por_metodo": por_metodo,
    }


def ventas_por_dia(desde, hasta):
    totales = {}
    filas = (
        ventas_del_periodo(desde, hasta)
        .annotate(dia=TruncDate("fecha"))
        .values("dia")
        .annotate(total=Sum("total"))
    )
    for fila in filas:
        totales[fila["dia"]] = fila["total"]

    dias = []
    dia = desde
    while dia <= hasta:
        dias.append({"fecha": dia, "total": totales.get(dia, 0)})
        dia += timedelta(days=1)

    mayor = max([d["total"] for d in dias] + [1])
    for d in dias:
        d["porcentaje"] = round(d["total"] * 100 / mayor)
    return dias


def productos_vendidos(desde, hasta):
    detalles = DetalleVenta.objects.filter(
        venta__in=ventas_del_periodo(desde, hasta), cantidad__isnull=False
    )
    return list(
        detalles.values("producto")
        .annotate(nombre=Max("nombre_producto"), cantidad=Sum("cantidad"), total=Sum("subtotal"))
        .order_by("-cantidad")
    )


def ventas_por_importe(desde, hasta):
    detalles = DetalleVenta.objects.filter(
        venta__in=ventas_del_periodo(desde, hasta), cantidad__isnull=True
    )
    return list(
        detalles.values("producto")
        .annotate(nombre=Max("nombre_producto"), veces=Count("id"), total=Sum("subtotal"))
        .order_by("-total")
    )


def resumen_compras(desde, hasta):
    compras = Compra.objects.filter(estado=Compra.ESTADO_CONFIRMADA, fecha__gte=desde, fecha__lte=hasta)
    detalles = DetalleCompra.objects.filter(compra__in=compras)

    por_tipo = []
    for valor, nombre in DetalleCompra.TIPOS:
        por_tipo.append({"nombre": nombre, "total": sumar(detalles.filter(tipo=valor), "subtotal")})

    return {
        "total": sumar(compras, "total"),
        "cantidad": compras.count(),
        "pendiente": sumar(compras.filter(estado_pago=Compra.PAGO_PENDIENTE), "total"),
        "por_tipo": por_tipo,
    }


def resumen_gastos(desde, hasta):
    gastos = Gasto.objects.filter(estado=Gasto.ESTADO_CONFIRMADO, fecha__gte=desde, fecha__lte=hasta)
    por_categoria = list(
        gastos.values("categoria__nombre").annotate(total=Sum("valor")).order_by("-total")
    )
    return {"total": sumar(gastos, "valor"), "cantidad": gastos.count(), "por_categoria": por_categoria}


def flujo_de_caja(desde, hasta):
    compras_pagadas = Compra.objects.filter(
        estado=Compra.ESTADO_CONFIRMADA,
        estado_pago=Compra.PAGO_PAGADA,
        fecha_pago__gte=desde,
        fecha_pago__lte=hasta,
    )
    movimientos = MovimientoCaja.objects.filter(fecha__gte=desde, fecha__lte=hasta)

    entradas = {
        "ventas": sumar(ventas_del_periodo(desde, hasta), "total"),
        "otras": sumar(movimientos.filter(tipo=MovimientoCaja.TIPO_INGRESO), "valor"),
    }
    salidas = {
        "gastos": resumen_gastos(desde, hasta)["total"],
        "compras": sumar(compras_pagadas, "total"),
        "otras": sumar(movimientos.filter(tipo=MovimientoCaja.TIPO_RETIRO), "valor"),
    }
    total_entradas = entradas["ventas"] + entradas["otras"]
    total_salidas = salidas["gastos"] + salidas["compras"] + salidas["otras"]
    return {
        "entradas": entradas,
        "salidas": salidas,
        "total_entradas": total_entradas,
        "total_salidas": total_salidas,
        "neto": total_entradas - total_salidas,
    }


def costo_promedio_compra(hasta, producto=None, insumo=None):
    detalles = DetalleCompra.objects.filter(compra__estado=Compra.ESTADO_CONFIRMADA, compra__fecha__lte=hasta)
    if producto:
        detalles = detalles.filter(producto=producto)
    else:
        detalles = detalles.filter(insumo=insumo)

    datos = detalles.aggregate(cantidad=Sum("cantidad"), total=Sum("subtotal"))
    if not datos["cantidad"]:
        return None
    return datos["total"] / datos["cantidad"]


def costo_de_reventa(vendidos, hasta, faltantes):
    costo = Decimal("0")
    sin_costo = []
    sin_control = []
    for fila in vendidos:
        producto = Producto.objects.filter(pk=fila["producto"]).first()
        if producto is None:
            continue
        if producto.control_inventario == Producto.CONTROL_NINGUNO:
            sin_control.append(fila["nombre"])
            continue
        if producto.control_inventario != Producto.CONTROL_UNIDADES:
            continue
        unitario = costo_promedio_compra(hasta, producto=producto)
        if unitario is None:
            sin_costo.append(fila["nombre"])
        else:
            costo += unitario * fila["cantidad"]

    if sin_control:
        faltantes.append(
            ", ".join(sin_control) + " no tienen costo registrado, así que se cuentan como si no costaran nada."
        )
    if sin_costo:
        faltantes.append(
            "No hay compras registradas de " + ", ".join(sin_costo)
            + ", así que su costo no se pudo descontar."
        )
    return round(costo)


def costo_de_insumos(desde, hasta, faltantes, hubo_ventas):
    consumos = ConsumoPreparacion.objects.filter(
        preparacion__estado=Preparacion.ESTADO_REGISTRADA,
        preparacion__fecha__gte=desde,
        preparacion__fecha__lte=hasta,
    ).values("insumo").annotate(cantidad=Sum("cantidad"))

    costo = Decimal("0")
    sin_costo = []
    for fila in consumos:
        insumo = Insumo.objects.get(pk=fila["insumo"])
        unitario = costo_promedio_compra(hasta, insumo=insumo) or insumo.costo_referencia
        if unitario is None:
            sin_costo.append(insumo.nombre)
        else:
            costo += unitario * fila["cantidad"]

    if hubo_ventas and not consumos:
        faltantes.append(
            "No se registraron insumos usados en producción, así que el costo del pan y demás productos "
            "de la panadería no está incluido."
        )
    if sin_costo:
        faltantes.append(
            "No hay compras ni costo de referencia de " + ", ".join(sin_costo) + "."
        )
    return round(costo)


def resultado_preliminar(desde, hasta, ventas_total, gastos_total, vendidos):
    faltantes = []
    costo_reventa = costo_de_reventa(vendidos, hasta, faltantes)
    costo_insumos = costo_de_insumos(desde, hasta, faltantes, ventas_total > 0)
    resultado = ventas_total - costo_reventa - costo_insumos - gastos_total
    return {
        "costo_reventa": costo_reventa,
        "costo_insumos": costo_insumos,
        "resultado": resultado,
        "faltantes": faltantes,
    }


def resumen_produccion(desde, hasta):
    preparaciones = Preparacion.objects.filter(
        estado=Preparacion.ESTADO_REGISTRADA, fecha__gte=desde, fecha__lte=hasta
    )
    por_nombre = list(
        preparaciones.values("nombre")
        .annotate(veces=Count("id"), bandejas=Sum("bandejas"), unidades=Sum("unidades_aproximadas"))
        .order_by("-veces")
    )
    return {
        "cantidad": preparaciones.count(),
        "bandejas": sumar(preparaciones, "bandejas"),
        "por_nombre": por_nombre,
    }


def resumen_inventario(desde, hasta):
    movimientos = MovimientoInventario.objects.filter(fecha__date__gte=desde, fecha__date__lte=hasta)
    nombres = dict(MovimientoInventario.TIPOS)
    por_tipo = [
        {"nombre": nombres[fila["tipo"]], "cantidad": fila["cantidad"]}
        for fila in movimientos.values("tipo").annotate(cantidad=Count("id")).order_by("tipo")
    ]
    ajustes = movimientos.filter(tipo=MovimientoInventario.TIPO_AJUSTE).select_related(
        "producto", "insumo", "usuario"
    )
    return {"total": movimientos.count(), "por_tipo": por_tipo, "ajustes": ajustes}


def armar_informe(tipo, fecha):
    desde, hasta = calcular_rango(tipo, fecha)
    ventas = resumen_ventas(desde, hasta)
    gastos = resumen_gastos(desde, hasta)
    vendidos = productos_vendidos(desde, hasta)

    anterior_desde, anterior_hasta = calcular_rango(tipo, fecha_anterior(tipo, fecha))
    ventas_anteriores = sumar(ventas_del_periodo(anterior_desde, anterior_hasta), "total")

    return {
        "tipo": tipo,
        "titulo": NOMBRES_TIPO[tipo],
        "desde": desde,
        "hasta": hasta,
        "ventas": ventas,
        "ventas_anteriores": ventas_anteriores,
        "diferencia_ventas": ventas["total"] - ventas_anteriores,
        "por_dia": ventas_por_dia(desde, hasta) if tipo != "diario" else [],
        "vendidos": vendidos,
        "por_importe": ventas_por_importe(desde, hasta),
        "compras": resumen_compras(desde, hasta),
        "gastos": gastos,
        "flujo": flujo_de_caja(desde, hasta),
        "resultado": resultado_preliminar(desde, hasta, ventas["total"], gastos["total"], vendidos),
        "produccion": resumen_produccion(desde, hasta),
        "inventario": resumen_inventario(desde, hasta),
    }
