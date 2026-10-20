from decimal import Decimal

from django import forms
from django.utils import timezone

from core.campos import CampoCantidad, CampoPesos
from core.opciones import METODOS_PAGO
from inventario.models import Insumo
from productos.models import Producto

from .models import Compra, Proveedor


def opciones_articulos():
    productos = Producto.objects.filter(activo=True, control_inventario=Producto.CONTROL_UNIDADES)
    insumos = Insumo.objects.filter(activo=True)
    return [
        ("", "Elija un artículo"),
        ("Productos para la venta", [(f"producto-{p.pk}", p.nombre) for p in productos]),
        ("Insumos de producción", [(f"insumo-{i.pk}", f"{i.nombre} ({i.unidad_medida})") for i in insumos]),
        ("Otros", [("otro", "Materiales u otro artículo (escribir)")]),
    ]


def unidades_articulos():
    unidades = {"otro": ""}
    productos = Producto.objects.filter(activo=True, control_inventario=Producto.CONTROL_UNIDADES)
    for producto in productos:
        unidades[f"producto-{producto.pk}"] = producto.unidad_medida
    for insumo in Insumo.objects.filter(activo=True):
        unidades[f"insumo-{insumo.pk}"] = insumo.unidad_medida
    return unidades


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "telefono"]


class CompraForm(forms.Form):
    fecha = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.filter(activo=True),
        required=False,
        empty_label="Sin proveedor",
    )
    estado_pago = forms.ChoiceField(
        label="¿Ya se pagó?",
        choices=[(Compra.PAGO_PAGADA, "Sí, ya se pagó"), (Compra.PAGO_PENDIENTE, "No, queda pendiente")],
        initial=Compra.PAGO_PAGADA,
        widget=forms.RadioSelect,
    )
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        choices=[("", "Elija")] + METODOS_PAGO,
        required=False,
        initial="efectivo",
    )
    observaciones = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["metodo_pago"].sin_opcional = True

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser futura.")
        return fecha

    def clean(self):
        datos = super().clean()
        if datos.get("estado_pago") == Compra.PAGO_PAGADA and not datos.get("metodo_pago"):
            self.add_error("metodo_pago", "Elija cómo se pagó.")
        if datos.get("estado_pago") == Compra.PAGO_PENDIENTE:
            datos["metodo_pago"] = ""
        return datos


class LineaCompraForm(forms.Form):
    articulo = forms.ChoiceField(label="Artículo")
    descripcion = forms.CharField(label="Descripción", max_length=150, required=False)
    cantidad = CampoCantidad(min_value=Decimal("0.001"))
    valor = CampoPesos(label="Valor pagado por esta línea")

    def __init__(self, *args, opciones=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["articulo"].choices = opciones or []

    def clean(self):
        datos = super().clean()
        if datos.get("articulo") == "otro" and not datos.get("descripcion", "").strip():
            self.add_error("descripcion", "Escriba qué se compró.")
        return datos


LineasCompraFormSet = forms.formset_factory(
    LineaCompraForm, extra=1, max_num=50, validate_max=True
)


class PagoForm(forms.Form):
    metodo_pago = forms.ChoiceField(label="Método de pago", choices=METODOS_PAGO)
    fecha_pago = forms.DateField(
        label="Fecha de pago",
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )


class AnulacionForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo de la anulación",
        max_length=255,
        help_text="Por ejemplo: se registró dos veces, el proveedor devolvió el dinero.",
    )


class FiltroComprasForm(forms.Form):
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    estado_pago = forms.ChoiceField(
        label="Pago",
        required=False,
        choices=[("", "Todos")] + Compra.ESTADOS_PAGO,
    )
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.all(),
        required=False,
        empty_label="Todos",
    )
