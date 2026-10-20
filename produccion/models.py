import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from inventario.models import Insumo
from productos.models import Producto


class Preparacion(models.Model):
    ESTADO_REGISTRADA = "registrada"
    ESTADO_ANULADA = "anulada"
    ESTADOS = [
        (ESTADO_REGISTRADA, "Registrada"),
        (ESTADO_ANULADA, "Anulada"),
    ]

    fecha = models.DateField(default=timezone.localdate)
    nombre = models.CharField("qué se preparó", max_length=120)
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, null=True, blank=True, verbose_name="producto relacionado"
    )
    bandejas = models.DecimalField("bandejas obtenidas", max_digits=6, decimal_places=1, null=True, blank=True)
    unidades_aproximadas = models.PositiveIntegerField("unidades aproximadas", null=True, blank=True)
    unidades_minimas = models.PositiveIntegerField("unidades mínimas estimadas", null=True, blank=True)
    unidades_maximas = models.PositiveIntegerField("unidades máximas estimadas", null=True, blank=True)
    observaciones = models.CharField(max_length=255, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="preparaciones")
    estado = models.CharField(max_length=12, choices=ESTADOS, default=ESTADO_REGISTRADA)
    codigo_operacion = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="preparaciones_anuladas",
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.CharField("motivo de anulación", max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "preparación"
        verbose_name_plural = "preparaciones"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(bandejas__isnull=True) | Q(bandejas__gt=0),
                name="preparacion_bandejas_positivas",
            ),
            models.CheckConstraint(
                condition=(
                    Q(unidades_minimas__isnull=True)
                    | Q(unidades_maximas__isnull=True)
                    | Q(unidades_minimas__lte=F("unidades_maximas"))
                ),
                name="preparacion_intervalo_valido",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.fecha:%d/%m/%Y})"

    @property
    def esta_anulada(self):
        return self.estado == self.ESTADO_ANULADA


class ConsumoPreparacion(models.Model):
    preparacion = models.ForeignKey(Preparacion, on_delete=models.PROTECT, related_name="consumos")
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        verbose_name = "insumo utilizado"
        verbose_name_plural = "insumos utilizados"
        constraints = [
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="consumo_cantidad_positiva"),
        ]

    def __str__(self):
        return f"{self.insumo.nombre}: {self.cantidad}"
