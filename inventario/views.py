from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.templatetags.formato import cantidad as formato_cantidad
from productos.models import Producto
from usuarios.permisos import solo_administrador

from . import servicios
from .forms import AjusteForm, FiltroMovimientosForm, InsumoForm
from .models import Insumo, MovimientoInventario


@solo_administrador
def panel_inventario(request):
    solo_alertas = request.GET.get("alertas") == "1"
    productos = servicios.productos_con_existencias()
    insumos = Insumo.objects.filter(activo=True)

    if solo_alertas:
        productos = [p for p in productos if p.estado_existencia != "normal"]
        insumos = [i for i in insumos if i.estado_existencia != "normal"]

    productos_alerta, insumos_alerta = servicios.articulos_con_alerta()

    return render(request, "inventario/panel.html", {
        "productos": productos,
        "insumos": insumos,
        "insumos_inactivos": Insumo.objects.filter(activo=False),
        "solo_alertas": solo_alertas,
        "total_alertas": len(productos_alerta) + len(insumos_alerta),
    })


@solo_administrador
def crear_insumo(request):
    formulario = InsumoForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        insumo = servicios.crear_insumo(formulario, request.user)
        messages.success(request, f"Insumo «{insumo.nombre}» guardado.")
        return redirect("inventario:panel")
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": "Nuevo insumo",
        "volver": "inventario:panel",
    })


@solo_administrador
def editar_insumo(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    formulario = InsumoForm(request.POST or None, instance=insumo)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, f"Cambios de «{insumo.nombre}» guardados.")
        return redirect("inventario:panel")
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": f"Editar {insumo.nombre}",
        "volver": "inventario:panel",
        "nota": "Para cambiar la existencia use la opción Ajustar. Así queda el registro del cambio.",
    })


@solo_administrador
@require_POST
def cambiar_estado_insumo(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    servicios.cambiar_estado_insumo(insumo, request.user)
    if insumo.activo:
        messages.success(request, f"«{insumo.nombre}» está activo otra vez.")
    else:
        messages.success(request, f"«{insumo.nombre}» quedó inactivo. Su historial se conserva.")
    return redirect("inventario:panel")


@solo_administrador
def ajustar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk, control_inventario=Producto.CONTROL_UNIDADES)
    return vista_ajuste(request, producto)


@solo_administrador
def ajustar_insumo(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    return vista_ajuste(request, insumo)


def vista_ajuste(request, articulo):
    formulario = AjusteForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            movimiento = servicios.ajustar_existencia(
                articulo,
                formulario.cleaned_data["existencia_contada"],
                formulario.cleaned_data["motivo"],
                request.user,
            )
        except ValidationError as error:
            formulario.add_error(None, error)
        else:
            messages.success(
                request,
                f"Existencia de «{articulo.nombre}» ajustada. Diferencia registrada: {formato_cantidad(movimiento.cantidad)} {articulo.unidad_medida}.",
            )
            return redirect("inventario:panel")
    return render(request, "inventario/ajuste.html", {"formulario": formulario, "articulo": articulo})


@solo_administrador
def lista_movimientos(request):
    filtro = FiltroMovimientosForm(request.GET or None)
    movimientos = MovimientoInventario.objects.select_related("producto", "insumo", "usuario")
    articulo = None
    tipo_articulo = ""

    producto_id = request.GET.get("producto")
    insumo_id = request.GET.get("insumo")
    if producto_id:
        articulo = get_object_or_404(Producto, pk=producto_id)
        tipo_articulo = "producto"
        movimientos = movimientos.filter(producto=articulo)
    elif insumo_id:
        articulo = get_object_or_404(Insumo, pk=insumo_id)
        tipo_articulo = "insumo"
        movimientos = movimientos.filter(insumo=articulo)

    if filtro.is_valid():
        if filtro.cleaned_data["tipo"]:
            movimientos = movimientos.filter(tipo=filtro.cleaned_data["tipo"])
        if filtro.cleaned_data["desde"]:
            movimientos = movimientos.filter(fecha__date__gte=filtro.cleaned_data["desde"])
        if filtro.cleaned_data["hasta"]:
            movimientos = movimientos.filter(fecha__date__lte=filtro.cleaned_data["hasta"])

    pagina = Paginator(movimientos, 50).get_page(request.GET.get("pagina"))
    parametros = request.GET.copy()
    parametros.pop("pagina", None)

    return render(request, "inventario/movimientos.html", {
        "filtro": filtro,
        "pagina": pagina,
        "articulo": articulo,
        "tipo_articulo": tipo_articulo,
        "parametros": parametros.urlencode(),
    })
