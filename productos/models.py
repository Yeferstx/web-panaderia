from django.db import models
from django.db.models import Q


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    FORMA_UNIDAD = "unidad"
    FORMA_IMPORTE = "importe"
    FORMAS_VENTA = [
        (FORMA_UNIDAD, "Por unidad"),
        (FORMA_IMPORTE, "Por importe (valor que paga el cliente)"),
    ]

    CONTROL_UNIDADES = "unidades"
    CONTROL_PRODUCCION = "produccion"
    CONTROL_NINGUNO = "ninguno"
    CONTROLES = [
        (CONTROL_UNIDADES, "Contar existencias por unidades"),
        (CONTROL_PRODUCCION, "Producción aproximada (sin existencias exactas)"),
        (CONTROL_NINGUNO, "Sin control de inventario"),
    ]

    UNIDADES = [
        ("und", "Unidad"),
        ("kg", "Kilogramo"),
        ("l", "Litro"),
    ]

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name="categoría")
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    precio_venta = models.DecimalField("precio de venta", max_digits=12, decimal_places=0, null=True, blank=True)
    forma_venta = models.CharField("forma de venta", max_length=10, choices=FORMAS_VENTA, default=FORMA_UNIDAD)
    control_inventario = models.CharField("control de inventario", max_length=12, choices=CONTROLES, default=CONTROL_NINGUNO)
    unidad_medida = models.CharField("unidad de medida", max_length=5, choices=UNIDADES, default="und")
    existencia = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    existencia_minima = models.DecimalField("existencia mínima", max_digits=10, decimal_places=3, default=0)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["categoria__nombre", "nombre"]
        constraints = [
            models.CheckConstraint(
                condition=Q(precio_venta__isnull=True) | Q(precio_venta__gt=0),
                name="producto_precio_positivo",
            ),
            models.CheckConstraint(
                condition=Q(forma_venta="importe") | Q(precio_venta__isnull=False),
                name="producto_unidad_con_precio",
            ),
            models.CheckConstraint(
                condition=~Q(forma_venta="importe", control_inventario="unidades"),
                name="producto_importe_sin_unidades",
            ),
            models.CheckConstraint(
                condition=Q(existencia_minima__gte=0),
                name="producto_minimo_no_negativo",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def lleva_existencias(self):
        return self.control_inventario == self.CONTROL_UNIDADES

    @property
    def estado_existencia(self):
        if not self.lleva_existencias:
            return ""
        if self.existencia < 0:
            return "negativo"
        if self.existencia == 0:
            return "agotado"
        if self.existencia <= self.existencia_minima:
            return "bajo"
        return "normal"
