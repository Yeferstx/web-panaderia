import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from inventario.models import Insumo
from usuarios.permisos import es_administrador, solo_administrador

from . import servicios
from .forms import AnulacionForm, ConsumosFormSet, FiltroProduccionForm, PreparacionForm
from .models import Preparacion


@login_required
def lista_produccion(request):
    hoy = timezone.localdate()
    desde = hoy - timedelta(days=6)
    hasta = hoy
    filtro = FiltroProduccionForm(request.GET or None, initial={"desde": desde, "hasta": hasta})
    if filtro.is_valid():
        desde = filtro.cleaned_data["desde"] or desde
        hasta = filtro.cleaned_data["hasta"] or hasta

    preparaciones = Preparacion.objects.filter(fecha__gte=desde, fecha__lte=hasta).select_related("usuario")
    registradas = preparaciones.filter(estado=Preparacion.ESTADO_REGISTRADA)
    pagina = Paginator(preparaciones.prefetch_related("consumos__insumo"), 50).get_page(request.GET.get("pagina"))
    parametros = request.GET.copy()
    parametros.pop("pagina", None)

    return render(request, "produccion/lista.html", {
        "filtro": filtro,
        "pagina": pagina,
        "desde": desde,
        "hasta": hasta,
        "total_preparaciones": registradas.count(),
        "total_bandejas": registradas.aggregate(total=Sum("bandejas"))["total"] or 0,
        "parametros": parametros.urlencode(),
    })


@login_required
def nueva_preparacion(request):
    if request.method == "POST":
        formulario = PreparacionForm(request.POST)
        consumos = ConsumosFormSet(request.POST, prefix="consumos")
        if formulario.is_valid() and consumos.is_valid():
            datos_consumos = [datos for datos in consumos.cleaned_data if datos]
            try:
                codigo = uuid.UUID(request.POST.get("codigo_operacion", ""))
                preparacion, advertencias, repetida = servicios.registrar_preparacion(
                    request.user, formulario.cleaned_data, datos_consumos, codigo
                )
            except ValueError:
                formulario.add_error(None, "No se pudo guardar. Recargue la página e intente de nuevo.")
            except ValidationError as error:
                formulario.add_error(None, error)
            else:
                if repetida:
                    messages.info(request, "Esa producción ya estaba guardada. No se registró dos veces.")
                else:
                    messages.success(request, f"Producción «{preparacion.nombre}» guardada.")
                for advertencia in advertencias:
                    messages.warning(request, advertencia)
                return redirect("produccion:lista")
    else:
        formulario = PreparacionForm()
        consumos = ConsumosFormSet(prefix="consumos")

    return render(request, "produccion/nueva.html", {
        "formulario": formulario,
        "consumos": consumos,
        "hay_insumos": Insumo.objects.filter(activo=True).exists(),
        "codigo_operacion": request.POST.get("codigo_operacion") or uuid.uuid4(),
    })


@login_required
def detalle_preparacion(request, pk):
    preparacion = get_object_or_404(Preparacion.objects.select_related("usuario", "producto", "anulada_por"), pk=pk)
    puede_anular = es_administrador(request.user) and not preparacion.esta_anulada
    return render(request, "produccion/detalle.html", {
        "preparacion": preparacion,
        "consumos": preparacion.consumos.select_related("insumo"),
        "formulario_anulacion": AnulacionForm() if puede_anular else None,
    })


@solo_administrador
@require_POST
def anular_preparacion(request, pk):
    preparacion = get_object_or_404(Preparacion, pk=pk)
    formulario = AnulacionForm(request.POST)
    if formulario.is_valid():
        try:
            servicios.anular_preparacion(preparacion, request.user, formulario.cleaned_data["motivo"])
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "Producción anulada. Los insumos usados volvieron al inventario.")
    else:
        messages.error(request, "Escriba el motivo de la anulación.")
    return redirect("produccion:detalle", pk=preparacion.pk)
