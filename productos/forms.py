from django import forms

from core.campos import CampoCantidad, CampoPesos

from .models import Categoria, Producto


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}


class ProductoForm(forms.ModelForm):
    precio_venta = CampoPesos(
        label="Precio de venta",
        required=False,
        help_text="Escríbalo sin puntos ni signo $. Si el producto se vende por importe, déjelo vacío.",
    )
    existencia_minima = CampoCantidad(
        label="Existencia mínima",
        required=False,
        min_value=0,
        help_text="Cuando queden esta cantidad o menos, el sistema avisa.",
    )
    existencia_inicial = CampoCantidad(
        label="Existencia inicial",
        required=False,
        min_value=0,
        help_text="Cuántas unidades hay ahora mismo. Solo si cuenta existencias por unidades.",
    )

    class Meta:
        model = Producto
        fields = [
            "nombre",
            "categoria",
            "descripcion",
            "forma_venta",
            "precio_venta",
            "control_inventario",
            "unidad_medida",
            "existencia_minima",
        ]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categorias = Categoria.objects.filter(activa=True)
        if self.instance.pk:
            categorias = categorias | Categoria.objects.filter(pk=self.instance.categoria_id)
            del self.fields["existencia_inicial"]
        self.fields["categoria"].queryset = categorias.distinct()
        self.fields["descripcion"].required = False
        self.fields["precio_venta"].sin_opcional = True

    def clean(self):
        datos = super().clean()
        forma = datos.get("forma_venta")
        control = datos.get("control_inventario")
        precio = datos.get("precio_venta")

        if forma == Producto.FORMA_IMPORTE:
            datos["precio_venta"] = None
            if control == Producto.CONTROL_UNIDADES:
                self.add_error(
                    "control_inventario",
                    "Un producto vendido por importe no puede contar existencias por unidades.",
                )
        elif forma == Producto.FORMA_UNIDAD and not precio:
            self.add_error("precio_venta", "Escriba el precio. Los productos por unidad necesitan precio.")

        if datos.get("existencia_minima") is None:
            datos["existencia_minima"] = 0

        inicial = datos.get("existencia_inicial")
        if inicial and control != Producto.CONTROL_UNIDADES:
            self.add_error(
                "existencia_inicial",
                "Solo los productos que cuentan existencias por unidades tienen existencia inicial.",
            )

        anterior = self.instance
        if (
            anterior.pk
            and anterior.control_inventario == Producto.CONTROL_UNIDADES
            and control != Producto.CONTROL_UNIDADES
            and anterior.existencia != 0
        ):
            self.add_error(
                "control_inventario",
                "Este producto todavía tiene existencias registradas. Ajústelas a 0 antes de cambiar el control.",
            )
        return datos
