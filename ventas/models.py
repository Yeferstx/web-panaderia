import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from productos.models import Producto


class Venta(models.Model):
    METODO_EFECTIVO = "efectivo"
    METODO_TRANSFERENCIA = "transferencia"
    METODO_OTROS = "otros"
    METODOS_PAGO = [
        (METODO_EFECTIVO, "Efectivo"),
        (METODO_TRANSFERENCIA, "Transferencia"),
        (METODO_OTROS, "Otros"),
    ]

    ESTADO_CONFIRMADA = "confirmada"
    ESTADO_ANULADA = "anulada"
    ESTADOS = [
        (ESTADO_CONFIRMADA, "Confirmada"),
        (ESTADO_ANULADA, "Anulada"),
    ]

    fecha = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ventas")
    total = models.DecimalField(max_digits=12, decimal_places=0)
    metodo_pago = models.CharField("método de pago", max_length=15, choices=METODOS_PAGO)
    estado = models.CharField(max_length=12, choices=ESTADOS, default=ESTADO_CONFIRMADA)
    observaciones = models.CharField(max_length=255, blank=True)
    codigo_operacion = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ventas_anuladas",
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.CharField("motivo de anulación", max_length=255, blank=True)

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(total__gt=0), name="venta_total_positivo"),
        ]

    def __str__(self):
        return f"Venta #{self.pk}"

    @property
    def esta_anulada(self):
        return self.estado == self.ESTADO_ANULADA


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    nombre_producto = models.CharField(max_length=120)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
        constraints = [
            models.CheckConstraint(condition=Q(subtotal__gt=0), name="detalle_subtotal_positivo"),
            models.CheckConstraint(
                condition=Q(cantidad__isnull=True) | Q(cantidad__gt=0),
                name="detalle_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=(
                    Q(cantidad__isnull=True, precio_unitario__isnull=True)
                    | Q(cantidad__isnull=False, precio_unitario__isnull=False)
                ),
                name="detalle_cantidad_y_precio_juntos",
            ),
        ]

    def __str__(self):
        return self.nombre_producto

    @property
    def es_por_importe(self):
        return self.cantidad is None
