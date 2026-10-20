from django import forms


class CampoPesos(forms.DecimalField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 12)
        kwargs.setdefault("decimal_places", 0)
        kwargs.setdefault("min_value", 1)
        super().__init__(**kwargs)
        self.widget = forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "Ej: 2500"})

    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace("$", "").replace(".", "").replace(",", "").replace(" ", "")
        return super().to_python(value)


class CampoCantidad(forms.DecimalField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 10)
        kwargs.setdefault("decimal_places", 3)
        super().__init__(**kwargs)
        self.widget = forms.TextInput(attrs={"inputmode": "decimal", "placeholder": "Ej: 20 o 2,5"})

    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(" ", "").replace(",", ".")
        return super().to_python(value)
