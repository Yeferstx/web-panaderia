from django.conf import settings
from django.db import models
from django.db.models import Q

from productos.models import Producto


class Insumo(models.Model):
    UNIDADES = [
        ("kg", "Kilogramos (kg)"),
        ("g", "Gramos (g)"),
        ("l", "Litros (l)"),
        ("ml", "Mililitros (ml)"),
        ("und", "Unidades"),
    ]

    nombre = models.CharField(max_length=100, unique=True)
    unidad_medida = models.CharField("unidad de medida", max_length=5, choices=UNIDADES)
    existencia = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    existencia_minima = models.DecimalField("existencia mínima", max_digits=10, decimal_places=3, default=0)
    costo_referencia = models.DecimalField(
        "costo de referencia por unidad de medida", max_digits=12, decimal_places=2, null=True, blank=True
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "insumo"
        verbose_name_plural = "insumos"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=Q(existencia_minima__gte=0),
                name="insumo_minimo_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(costo_referencia__isnull=True) | Q(costo_referencia__gte=0),
                name="insumo_costo_no_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.unidad_medida})"

    @property
    def lleva_existencias(self):
        return True

    @property
    def estado_existencia(self):
        if self.existencia < 0:
            return "negativo"
        if self.existencia == 0:
            return "agotado"
        if self.existencia <= self.existencia_minima:
            return "bajo"
        return "normal"


class MovimientoInventario(models.Model):
    TIPO_INICIAL = "inicial"
    TIPO_ENTRADA = "entrada"
    TIPO_SALIDA = "salida"
    TIPO_AJUSTE = "ajuste"
    TIPO_ANULACION = "anulacion"
    TIPOS = [
        (TIPO_INICIAL, "Existencia inicial"),
        (TIPO_ENTRADA, "Entrada"),
        (TIPO_SALIDA, "Salida"),
        (TIPO_AJUSTE, "Ajuste"),
        (TIPO_ANULACION, "Anulación"),
    ]

    ORIGENES = [
        ("", "Manual"),
        ("venta", "Venta"),
        ("compra", "Compra"),
        ("produccion", "Producción"),
    ]

    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos"
    )
    insumo = models.ForeignKey(
        Insumo, on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos"
    )
    tipo = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    existencia_anterior = models.DecimalField(max_digits=10, decimal_places=3)
    existencia_resultante = models.DecimalField(max_digits=10, decimal_places=3)
    motivo = models.CharField(max_length=255)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    origen = models.CharField(max_length=12, choices=ORIGENES, blank=True)
    origen_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(producto__isnull=False, insumo__isnull=True)
                    | Q(producto__isnull=True, insumo__isnull=False)
                ),
                name="movimiento_un_solo_articulo",
            ),
            models.CheckConstraint(
                condition=~Q(cantidad=0),
                name="movimiento_cantidad_distinta_de_cero",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.articulo}: {self.cantidad}"

    @property
    def articulo(self):
        return self.producto or self.insumo

    @property
    def unidad(self):
        return self.articulo.unidad_medida
