import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.templatetags.formato import pesos
from productos.models import Categoria, Producto
from usuarios.permisos import es_administrador, solo_administrador

from . import servicios
from .forms import AnulacionForm, FiltroVentasForm
from .models import Venta


def datos_productos_para_venta():
    productos = Producto.objects.filter(activo=True, categoria__activa=True).select_related("categoria")
    datos = []
    for producto in productos:
        datos.append({
            "id": producto.pk,
            "nombre": producto.nombre,
            "categoria": producto.categoria_id,
            "por_importe": producto.forma_venta == Producto.FORMA_IMPORTE,
            "precio": int(producto.precio_venta) if producto.precio_venta else None,
            "unidad": producto.unidad_medida,
            "lleva_existencias": producto.lleva_existencias,
            "existencia": float(producto.existencia),
        })
    return datos


@login_required
def nueva_venta(request):
    lineas_enviadas = "[]"
    metodo_pago = Venta.METODO_EFECTIVO
    observaciones = ""
    error = ""

    if request.method == "POST":
        lineas_enviadas = request.POST.get("lineas", "[]")
        metodo_pago = request.POST.get("metodo_pago", "")
        observaciones = request.POST.get("observaciones", "")
        try:
            codigo = uuid.UUID(request.POST.get("codigo_operacion", ""))
        except ValueError:
            codigo = None

        if codigo is None:
            error = "No se pudo guardar la venta. Recargue la página e intente de nuevo."
        else:
            try:
                venta, advertencias, repetida = servicios.registrar_venta(
                    request.user, lineas_enviadas, metodo_pago, observaciones, codigo
                )
            except ValidationError as excepcion:
                error = " ".join(excepcion.messages)
            else:
                if repetida:
                    messages.info(request, f"La venta #{venta.pk} ya estaba guardada. No se registró dos veces.")
                else:
                    messages.success(request, f"Venta #{venta.pk} guardada por {pesos(venta.total)}.")
                for advertencia in advertencias:
                    messages.warning(request, advertencia)
                return redirect("ventas:nueva")

    return render(request, "ventas/nueva.html", {
        "productos": datos_productos_para_venta(),
        "categorias": Categoria.objects.filter(activa=True),
        "metodos_pago": Venta.METODOS_PAGO,
        "metodo_pago": metodo_pago,
        "observaciones": observaciones,
        "lineas_enviadas": lineas_enviadas,
        "codigo_operacion": uuid.uuid4(),
        "error": error,
    })


@login_required
def lista_ventas(request):
    administrador = es_administrador(request.user)
    hoy = timezone.localdate()
    filtro = FiltroVentasForm(request.GET or None, initial={"desde": hoy, "hasta": hoy})

    ventas = Venta.objects.select_related("usuario")
    desde = hoy
    hasta = hoy

    if not administrador:
        ventas = ventas.filter(usuario=request.user)
    elif filtro.is_valid():
        desde = filtro.cleaned_data["desde"] or hoy
        hasta = filtro.cleaned_data["hasta"] or desde
        if filtro.cleaned_data["metodo_pago"]:
            ventas = ventas.filter(metodo_pago=filtro.cleaned_data["metodo_pago"])
        if filtro.cleaned_data["estado"]:
            ventas = ventas.filter(estado=filtro.cleaned_data["estado"])

    ventas = ventas.filter(fecha__date__gte=desde, fecha__date__lte=hasta)
    resumen = ventas.filter(estado=Venta.ESTADO_CONFIRMADA).aggregate(total=Sum("total"), cantidad=Count("id"))
    pagina = Paginator(ventas, 50).get_page(request.GET.get("pagina"))
    parametros = request.GET.copy()
    parametros.pop("pagina", None)

    return render(request, "ventas/lista.html", {
        "filtro": filtro,
        "pagina": pagina,
        "resumen": resumen,
        "desde": desde,
        "hasta": hasta,
        "parametros": parametros.urlencode(),
    })


@login_required
def detalle_venta(request, pk):
    venta = get_object_or_404(Venta.objects.select_related("usuario", "anulada_por"), pk=pk)
    administrador = es_administrador(request.user)
    if not administrador and venta.usuario != request.user:
        raise PermissionDenied

    return render(request, "ventas/detalle.html", {
        "venta": venta,
        "detalles": venta.detalles.all(),
        "formulario_anulacion": AnulacionForm() if administrador and not venta.esta_anulada else None,
    })


@solo_administrador
@require_POST
def anular_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    formulario = AnulacionForm(request.POST)
    if formulario.is_valid():
        try:
            servicios.anular_venta(venta, request.user, formulario.cleaned_data["motivo"])
        except ValidationError as excepcion:
            messages.error(request, " ".join(excepcion.messages))
        else:
            messages.success(request, f"Venta #{venta.pk} anulada. Las existencias de las bebidas se devolvieron.")
    else:
        messages.error(request, "Escriba el motivo de la anulación.")
    return redirect("ventas:detalle", pk=venta.pk)
