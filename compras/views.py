import uuid
from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.actividad import registrar_actividad
from core.templatetags.formato import pesos
from usuarios.permisos import solo_administrador

from . import servicios
from .forms import (
    AnulacionForm,
    CompraForm,
    FiltroComprasForm,
    LineasCompraFormSet,
    PagoForm,
    ProveedorForm,
    opciones_articulos,
    unidades_articulos,
)
from .models import Compra, Proveedor


@solo_administrador
def lista_compras(request):
    hoy = timezone.localdate()
    desde = hoy - timedelta(days=30)
    hasta = hoy
    filtro = FiltroComprasForm(request.GET or None, initial={"desde": desde, "hasta": hasta})
    compras = Compra.objects.select_related("proveedor", "usuario")

    if filtro.is_valid():
        desde = filtro.cleaned_data["desde"] or desde
        hasta = filtro.cleaned_data["hasta"] or hasta
        if filtro.cleaned_data["estado_pago"]:
            compras = compras.filter(estado_pago=filtro.cleaned_data["estado_pago"])
        if filtro.cleaned_data["proveedor"]:
            compras = compras.filter(proveedor=filtro.cleaned_data["proveedor"])

    compras = compras.filter(fecha__gte=desde, fecha__lte=hasta)
    confirmadas = compras.filter(estado=Compra.ESTADO_CONFIRMADA)
    pendientes_todas = Compra.objects.filter(estado=Compra.ESTADO_CONFIRMADA, estado_pago=Compra.PAGO_PENDIENTE)

    pagina = Paginator(compras, 50).get_page(request.GET.get("pagina"))
    parametros = request.GET.copy()
    parametros.pop("pagina", None)

    return render(request, "compras/lista.html", {
        "filtro": filtro,
        "pagina": pagina,
        "desde": desde,
        "hasta": hasta,
        "total_compras": confirmadas.aggregate(total=Sum("total"))["total"] or 0,
        "total_pendiente": pendientes_todas.aggregate(total=Sum("total"))["total"] or 0,
        "cantidad_pendientes": pendientes_todas.count(),
        "parametros": parametros.urlencode(),
    })


@solo_administrador
def nueva_compra(request):
    opciones = opciones_articulos()
    if request.method == "POST":
        formulario = CompraForm(request.POST)
        lineas = LineasCompraFormSet(request.POST, prefix="lineas", form_kwargs={"opciones": opciones})
        if formulario.is_valid() and lineas.is_valid():
            datos_lineas = [datos for datos in lineas.cleaned_data if datos]
            try:
                codigo = uuid.UUID(request.POST.get("codigo_operacion", ""))
                compra, repetida = servicios.registrar_compra(
                    request.user, formulario.cleaned_data, datos_lineas, codigo
                )
            except ValueError:
                formulario.add_error(None, "No se pudo guardar. Recargue la página e intente de nuevo.")
            except ValidationError as error:
                formulario.add_error(None, error)
            else:
                if repetida:
                    messages.info(request, f"La compra #{compra.pk} ya estaba guardada. No se registró dos veces.")
                else:
                    messages.success(request, f"Compra #{compra.pk} guardada por {pesos(compra.total)}.")
                return redirect("compras:detalle", pk=compra.pk)
    else:
        formulario = CompraForm()
        lineas = LineasCompraFormSet(prefix="lineas", form_kwargs={"opciones": opciones})

    return render(request, "compras/nueva.html", {
        "formulario": formulario,
        "lineas": lineas,
        "unidades": unidades_articulos(),
        "codigo_operacion": request.POST.get("codigo_operacion") or uuid.uuid4(),
    })


@solo_administrador
def detalle_compra(request, pk):
    compra = get_object_or_404(Compra.objects.select_related("proveedor", "usuario", "anulada_por"), pk=pk)
    return render(request, "compras/detalle.html", {
        "compra": compra,
        "detalles": compra.detalles.all(),
        "formulario_pago": PagoForm() if compra.esta_pendiente and not compra.esta_anulada else None,
        "formulario_anulacion": AnulacionForm() if not compra.esta_anulada else None,
    })


@solo_administrador
@require_POST
def pagar_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    formulario = PagoForm(request.POST)
    if formulario.is_valid():
        try:
            servicios.registrar_pago(
                compra, formulario.cleaned_data["metodo_pago"], formulario.cleaned_data["fecha_pago"], request.user
            )
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, f"Compra #{compra.pk} marcada como pagada.")
    else:
        messages.error(request, "Revise el método y la fecha de pago.")
    return redirect("compras:detalle", pk=compra.pk)


@solo_administrador
@require_POST
def anular_compra(request, pk):
    compra = get_object_or_404(Compra, pk=pk)
    formulario = AnulacionForm(request.POST)
    if formulario.is_valid():
        try:
            servicios.anular_compra(compra, request.user, formulario.cleaned_data["motivo"])
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, f"Compra #{compra.pk} anulada. Lo que había sumado al inventario se descontó.")
    else:
        messages.error(request, "Escriba el motivo de la anulación.")
    return redirect("compras:detalle", pk=compra.pk)


@solo_administrador
def lista_proveedores(request):
    return render(request, "compras/proveedores.html", {"proveedores": Proveedor.objects.all()})


@solo_administrador
def crear_proveedor(request):
    formulario = ProveedorForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        proveedor = formulario.save()
        messages.success(request, f"Proveedor «{proveedor.nombre}» guardado.")
        return redirect("compras:proveedores")
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": "Nuevo proveedor",
        "volver": "compras:proveedores",
    })


@solo_administrador
def editar_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    formulario = ProveedorForm(request.POST or None, instance=proveedor)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, f"Cambios de «{proveedor.nombre}» guardados.")
        return redirect("compras:proveedores")
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": f"Editar {proveedor.nombre}",
        "volver": "compras:proveedores",
    })


@solo_administrador
@require_POST
def cambiar_estado_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    proveedor.activo = not proveedor.activo
    proveedor.save(update_fields=["activo", "actualizado_en"])
    accion = "Proveedor activado" if proveedor.activo else "Proveedor desactivado"
    registrar_actividad(request.user, accion, proveedor.nombre)
    messages.success(request, f"{accion}: {proveedor.nombre}.")
    return redirect("compras:proveedores")
