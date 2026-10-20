from django import forms

from core.campos import CampoCantidad, CampoPesos

from .models import Insumo, MovimientoInventario


class InsumoForm(forms.ModelForm):
    existencia_minima = CampoCantidad(
        label="Existencia mínima",
        required=False,
        min_value=0,
        help_text="Cuando quede esta cantidad o menos, el sistema avisa.",
    )
    costo_referencia = CampoPesos(
        label="Costo de referencia",
        required=False,
        min_value=0,
        help_text="Precio aproximado por cada unidad de medida, por ejemplo por kg. Es opcional.",
    )
    existencia_inicial = CampoCantidad(
        label="Existencia inicial",
        required=False,
        min_value=0,
        help_text="Cuánto hay ahora mismo en la bodega, en la unidad elegida.",
    )

    class Meta:
        model = Insumo
        fields = ["nombre", "unidad_medida", "existencia_minima", "costo_referencia"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            del self.fields["existencia_inicial"]

    def clean_existencia_minima(self):
        return self.cleaned_data.get("existencia_minima") or 0

    def clean_unidad_medida(self):
        unidad = self.cleaned_data["unidad_medida"]
        insumo = self.instance
        if insumo.pk and unidad != insumo.unidad_medida and insumo.movimientos.exists():
            raise forms.ValidationError(
                "No se puede cambiar la unidad porque el insumo ya tiene movimientos registrados."
            )
        return unidad


class AjusteForm(forms.Form):
    existencia_contada = CampoCantidad(
        label="Cantidad contada",
        min_value=0,
        help_text="Lo que hay realmente al contar.",
    )
    motivo = forms.CharField(
        max_length=255,
        help_text="Por ejemplo: conteo físico del lunes, producto dañado, error de registro.",
    )


class FiltroMovimientosForm(forms.Form):
    tipo = forms.ChoiceField(
        required=False,
        choices=[("", "Todos los tipos")] + MovimientoInventario.TIPOS,
    )
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
