from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from compras.models import Compra
from gastos.models import Gasto
from inventario.servicios import articulos_con_alerta
from produccion.models import Preparacion
from reportes import servicios as reportes
from usuarios.permisos import es_administrador
from ventas.models import Venta


@login_required
def inicio(request):
    hoy = timezone.localdate()
    ventas_hoy = reportes.ventas_del_periodo(hoy, hoy)
    datos = {"hoy": hoy}

    if not es_administrador(request.user):
        mis_ventas = ventas_hoy.filter(usuario=request.user)
        datos["mis_ventas_total"] = reportes.sumar(mis_ventas, "total")
        datos["mis_ventas_cantidad"] = mis_ventas.count()
        datos["produccion_hoy"] = Preparacion.objects.filter(
            fecha=hoy, estado=Preparacion.ESTADO_REGISTRADA
        ).count()
        return render(request, "core/inicio.html", datos)

    inicio_mes, fin_mes = reportes.calcular_rango("mensual", hoy)
    inicio_semana, fin_semana = reportes.calcular_rango("semanal", hoy)
    semana_pasada = reportes.calcular_rango("semanal", hoy - timedelta(days=7))
    productos_alerta, insumos_alerta = articulos_con_alerta()
    compras_mes = Compra.objects.filter(
        estado=Compra.ESTADO_CONFIRMADA, fecha__gte=inicio_mes, fecha__lte=fin_mes
    )
    pendientes = Compra.objects.filter(estado=Compra.ESTADO_CONFIRMADA, estado_pago=Compra.PAGO_PENDIENTE)

    datos.update({
        "ventas_hoy": reportes.resumen_ventas(hoy, hoy),
        "gastos_hoy": reportes.sumar(
            Gasto.objects.filter(fecha=hoy, estado=Gasto.ESTADO_CONFIRMADO), "valor"
        ),
        "compras_mes": reportes.sumar(compras_mes, "total"),
        "pendientes_total": reportes.sumar(pendientes, "total"),
        "pendientes_cantidad": pendientes.count(),
        "alertas": len(productos_alerta) + len(insumos_alerta),
        "semana_total": reportes.sumar(reportes.ventas_del_periodo(inicio_semana, fin_semana), "total"),
        "semana_pasada_total": reportes.sumar(reportes.ventas_del_periodo(*semana_pasada), "total"),
        "semana_dias": reportes.ventas_por_dia(inicio_semana, fin_semana),
        "ultimas_ventas": ventas_hoy.select_related("usuario")[:6],
    })
    return render(request, "core/inicio.html", datos)
