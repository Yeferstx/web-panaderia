from decimal import Decimal

from django import forms
from django.utils import timezone

from core.campos import CampoCantidad
from inventario.models import Insumo
from productos.models import Producto


class PreparacionForm(forms.Form):
    fecha = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    nombre = forms.CharField(
        label="¿Qué se preparó?",
        max_length=120,
        help_text="Por ejemplo: pan blandito, masa de hojaldre, galletas.",
    )
    producto = forms.ModelChoiceField(
        label="Producto relacionado",
        queryset=Producto.objects.none(),
        required=False,
        empty_label="Ninguno",
        help_text="Opcional. Sirve para los informes de producción por producto.",
    )
    bandejas = CampoCantidad(
        label="Bandejas obtenidas",
        required=False,
        min_value=Decimal("0.1"),
        max_digits=6,
        decimal_places=1,
    )
    unidades_aproximadas = forms.IntegerField(label="Unidades aproximadas", required=False, min_value=1)
    unidades_minimas = forms.IntegerField(label="Desde (unidades)", required=False, min_value=1)
    unidades_maximas = forms.IntegerField(label="Hasta (unidades)", required=False, min_value=1)
    observaciones = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = Producto.objects.filter(
            activo=True, control_inventario=Producto.CONTROL_PRODUCCION
        )

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser futura.")
        return fecha

    def clean(self):
        datos = super().clean()
        minimas = datos.get("unidades_minimas")
        maximas = datos.get("unidades_maximas")
        if minimas and maximas and minimas > maximas:
            self.add_error("unidades_maximas", "El «hasta» debe ser mayor o igual que el «desde».")
        if (minimas and not maximas) or (maximas and not minimas):
            self.add_error("unidades_maximas", "Si usa un intervalo, escriba el «desde» y el «hasta».")
        return datos


class ConsumoForm(forms.Form):
    insumo = forms.ModelChoiceField(queryset=Insumo.objects.none(), empty_label="Elija un insumo")
    cantidad = CampoCantidad(min_value=Decimal("0.001"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["insumo"].queryset = Insumo.objects.filter(activo=True)
        self.fields["insumo"].label_from_instance = lambda insumo: f"{insumo.nombre} ({insumo.unidad_medida})"


ConsumosFormSet = forms.formset_factory(ConsumoForm, extra=1, max_num=30, validate_max=True)


class AnulacionForm(forms.Form):
    motivo = forms.CharField(label="Motivo de la anulación", max_length=255)


class FiltroProduccionForm(forms.Form):
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
