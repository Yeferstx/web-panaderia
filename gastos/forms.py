from django import forms
from django.utils import timezone

from core.campos import CampoPesos
from core.opciones import METODOS_PAGO

from .models import CategoriaGasto, Gasto, MovimientoCaja


def validar_fecha_no_futura(fecha):
    if fecha > timezone.localdate():
        raise forms.ValidationError("La fecha no puede ser futura.")
    return fecha


class GastoForm(forms.ModelForm):
    valor = CampoPesos(help_text="Sin puntos ni signo $.")
    metodo_pago = forms.ChoiceField(label="Método de pago", choices=METODOS_PAGO, initial="efectivo")

    class Meta:
        model = Gasto
        fields = ["fecha", "categoria", "descripcion", "valor", "metodo_pago", "observaciones"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        help_texts = {
            "descripcion": "Por ejemplo: recibo de la luz de octubre, transporte del pedido.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = CategoriaGasto.objects.filter(activa=True)
        self.fields["fecha"].initial = timezone.localdate()

    def clean_fecha(self):
        return validar_fecha_no_futura(self.cleaned_data["fecha"])


class CategoriaGastoForm(forms.ModelForm):
    class Meta:
        model = CategoriaGasto
        fields = ["nombre"]


class AnulacionForm(forms.Form):
    motivo = forms.CharField(label="Motivo de la anulación", max_length=255)


class FiltroGastosForm(forms.Form):
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    categoria = forms.ModelChoiceField(
        label="Categoría",
        queryset=CategoriaGasto.objects.all(),
        required=False,
        empty_label="Todas",
    )


class MovimientoCajaForm(forms.ModelForm):
    tipo = forms.ChoiceField(choices=MovimientoCaja.TIPOS)
    valor = CampoPesos()

    class Meta:
        model = MovimientoCaja
        fields = ["tipo", "valor", "motivo"]
        help_texts = {
            "motivo": "Por ejemplo: el dueño sacó dinero, se agregó sencillo para cambio.",
        }


class CierreCajaForm(forms.Form):
    saldo_inicial = CampoPesos(
        label="Efectivo con el que abrió la caja",
        min_value=0,
        help_text="Por defecto es lo que se contó en el cierre anterior.",
    )
    efectivo_contado = CampoPesos(
        label="Efectivo contado al cerrar",
        min_value=0,
        help_text="Cuente los billetes y monedas que hay en la caja.",
    )
    observaciones = forms.CharField(max_length=255, required=False)


class FechaCajaForm(forms.Form):
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
