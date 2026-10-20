from django import forms

from .models import Venta


class FiltroVentasForm(forms.Form):
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        required=False,
        choices=[("", "Todos")] + Venta.METODOS_PAGO,
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[("", "Todas")] + Venta.ESTADOS,
    )


class AnulacionForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo de la anulación",
        max_length=255,
        help_text="Por ejemplo: se registró dos veces, el cliente devolvió el producto.",
    )
