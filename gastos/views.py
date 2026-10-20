import uuid

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.actividad import registrar_actividad
from core.templatetags.formato import pesos
from usuarios.permisos import solo_administrador

from . import servicios
from .forms import (
    AnulacionForm,
    CategoriaGastoForm,
    CierreCajaForm,
    FechaCajaForm,
    FiltroGastosForm,
    GastoForm,
    MovimientoCajaForm,
)
from .models import CategoriaGasto, CierreCaja, Gasto, MovimientoCaja


@solo_administrador
def lista_gastos(request):
    hoy = timezone.localdate()
    desde = hoy.replace(day=1)
    hasta = hoy
    filtro = FiltroGastosForm(request.GET or None, initial={"desde": desde, "hasta": hasta})
    gastos = Gasto.objects.select_related("categoria", "usuario")

    if filtro.is_valid():
        desde = filtro.cleaned_data["desde"] or desde
        hasta = filtro.cleaned_data["hasta"] or hasta
        if filtro.cleaned_data["categoria"]:
            gastos = gastos.filter(categoria=filtro.cleaned_data["categoria"])

    gastos = gastos.filter(fecha__gte=desde, fecha__lte=hasta)
    total = gastos.filter(estado=Gasto.ESTADO_CONFIRMADO).aggregate(total=Sum("valor"))["total"] or 0
    pagina = Paginator(gastos, 50).get_page(request.GET.get("pagina"))
    parametros = request.GET.copy()
    parametros.pop("pagina", None)

    return render(request, "gastos/lista.html", {
        "filtro": filtro,
        "pagina": pagina,
        "total": total,
        "desde": desde,
        "hasta": hasta,
        "parametros": parametros.urlencode(),
    })


@solo_administrador
def nuevo_gasto(request):
    formulario = GastoForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            codigo = uuid.UUID(request.POST.get("codigo_operacion", ""))
        except ValueError:
            formulario.add_error(None, "No se pudo guardar. Recargue la página e intente de nuevo.")
        else:
            gasto, repetido = servicios.registrar_gasto(request.user, formulario.cleaned_data, codigo)
            if repetido:
                messages.info(request, "Ese gasto ya estaba guardado. No se registró dos veces.")
            else:
                messages.success(request, f"Gasto «{gasto.descripcion}» guardado por {pesos(gasto.valor)}.")
            return redirect("gastos:lista")
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": "Registrar gasto",
        "volver": "gastos:lista",
        "nota": "Aquí van los pagos generales: servicios, transporte, mantenimiento. "
                "Las compras de harina, bebidas y demás artículos se registran en Compras para no contarlas dos veces.",
        "codigo_operacion": request.POST.get("codigo_operacion") or uuid.uuid4(),
    })


@solo_administrador
def detalle_gasto(request, pk):
    gasto = get_object_or_404(Gasto.objects.select_related("categoria", "usuario", "anulado_por"), pk=pk)
    return render(request, "gastos/detalle.html", {
        "gasto": gasto,
        "formulario_anulacion": AnulacionForm() if not gasto.esta_anulado else None,
    })


@solo_administrador
@require_POST
def anular_gasto(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    formulario = AnulacionForm(request.POST)
    if formulario.is_valid():
        try:
            servicios.anular_gasto(gasto, request.user, formulario.cleaned_data["motivo"])
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "Gasto anulado. Ya no se suma en los totales.")
    else:
        messages.error(request, "Escriba el motivo de la anulación.")
    return redirect("gastos:detalle", pk=gasto.pk)


@solo_administrador
def categorias_gasto(request):
    formulario = CategoriaGastoForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        categoria = formulario.save()
        messages.success(request, f"Categoría «{categoria.nombre}» guardada.")
        return redirect("gastos:categorias")
    return render(request, "gastos/categorias.html", {
        "formulario": formulario,
        "categorias": CategoriaGasto.objects.all(),
    })


@solo_administrador
@require_POST
def cambiar_estado_categoria(request, pk):
    categoria = get_object_or_404(CategoriaGasto, pk=pk)
    categoria.activa = not categoria.activa
    categoria.save(update_fields=["activa"])
    accion = "Categoría de gasto activada" if categoria.activa else "Categoría de gasto desactivada"
    registrar_actividad(request.user, accion, categoria.nombre)
    messages.success(request, f"{accion}: {categoria.nombre}.")
    return redirect("gastos:categorias")


def leer_fecha_caja(request):
    formulario = FechaCajaForm(request.GET or request.POST or None)
    if formulario.is_valid():
        return formulario.cleaned_data["fecha"]
    return timezone.localdate()


def url_caja(fecha):
    return f"{reverse('gastos:caja')}?fecha={fecha:%Y-%m-%d}"


@solo_administrador
def caja(request):
    fecha = leer_fecha_caja(request)
    cierre = CierreCaja.objects.select_related("usuario").filter(fecha=fecha).first()
    hay_cambios = False

    if cierre:
        resumen = servicios.calcular_caja(fecha, cierre.saldo_inicial)
        hay_cambios = resumen["efectivo_esperado"] != cierre.efectivo_esperado
        formulario_cierre = None
    else:
        saldo = servicios.saldo_inicial_sugerido(fecha)
        resumen = servicios.calcular_caja(fecha, saldo)
        formulario_cierre = CierreCajaForm(initial={"saldo_inicial": saldo})

    return render(request, "gastos/caja.html", {
        "fecha": fecha,
        "es_hoy": fecha == timezone.localdate(),
        "es_futura": fecha > timezone.localdate(),
        "resumen": resumen,
        "cierre": cierre,
        "hay_cambios": hay_cambios,
        "formulario_cierre": formulario_cierre,
        "formulario_movimiento": MovimientoCajaForm() if not cierre else None,
        "movimientos": MovimientoCaja.objects.filter(fecha=fecha).select_related("usuario"),
    })


@solo_administrador
@require_POST
def cerrar_caja(request):
    fecha = leer_fecha_caja(request)
    formulario = CierreCajaForm(request.POST)
    if formulario.is_valid():
        try:
            cierre = servicios.cerrar_caja(
                fecha,
                formulario.cleaned_data["saldo_inicial"],
                formulario.cleaned_data["efectivo_contado"],
                formulario.cleaned_data["observaciones"],
                request.user,
            )
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            if cierre.diferencia == 0:
                messages.success(request, "Caja cerrada. El efectivo contado coincide con el esperado.")
            else:
                messages.warning(request, f"Caja cerrada con una diferencia de {pesos(cierre.diferencia)}.")
    else:
        messages.error(request, "Revise los valores del cierre. Escríbalos sin puntos ni signo $.")
    return redirect(url_caja(fecha))


@solo_administrador
@require_POST
def nuevo_movimiento_caja(request):
    fecha = leer_fecha_caja(request)
    formulario = MovimientoCajaForm(request.POST)
    if fecha > timezone.localdate():
        messages.error(request, "No se pueden registrar movimientos en un día futuro.")
    elif CierreCaja.objects.filter(fecha=fecha).exists():
        messages.error(request, "La caja de ese día ya está cerrada.")
    elif formulario.is_valid():
        movimiento = formulario.save(commit=False)
        movimiento.fecha = fecha
        movimiento.usuario = request.user
        movimiento.save()
        registrar_actividad(
            request.user, "Movimiento de caja", f"{movimiento.get_tipo_display()} de {pesos(movimiento.valor)}: {movimiento.motivo}"
        )
        messages.success(request, f"{movimiento.get_tipo_display()} de {pesos(movimiento.valor)} registrada.")
    else:
        messages.error(request, "Revise el tipo, el valor y el motivo del movimiento.")
    return redirect(url_caja(fecha))
