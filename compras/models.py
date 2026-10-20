import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.opciones import METODOS_PAGO
from inventario.models import Insumo
from productos.models import Producto


class Proveedor(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    ESTADO_CONFIRMADA = "confirmada"
    ESTADO_ANULADA = "anulada"
    ESTADOS = [
        (ESTADO_CONFIRMADA, "Confirmada"),
        (ESTADO_ANULADA, "Anulada"),
    ]

    PAGO_PAGADA = "pagada"
    PAGO_PENDIENTE = "pendiente"
    ESTADOS_PAGO = [
        (PAGO_PAGADA, "Pagada"),
        (PAGO_PENDIENTE, "Pendiente de pago"),
    ]

    fecha = models.DateField(default=timezone.localdate)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="compras")
    total = models.DecimalField(max_digits=12, decimal_places=0)
    estado = models.CharField(max_length=12, choices=ESTADOS, default=ESTADO_CONFIRMADA)
    estado_pago = models.CharField("estado del pago", max_length=10, choices=ESTADOS_PAGO)
    metodo_pago = models.CharField("método de pago", max_length=15, choices=METODOS_PAGO, blank=True)
    fecha_pago = models.DateField("fecha de pago", null=True, blank=True)
    observaciones = models.CharField(max_length=255, blank=True)
    codigo_operacion = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="compras_anuladas",
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.CharField("motivo de anulación", max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "compra"
        verbose_name_plural = "compras"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(total__gt=0), name="compra_total_positivo"),
            models.CheckConstraint(
                condition=(
                    Q(estado_pago="pagada", fecha_pago__isnull=False) & ~Q(metodo_pago="")
                    | Q(estado_pago="pendiente", fecha_pago__isnull=True, metodo_pago="")
                ),
                name="compra_pago_coherente",
            ),
        ]

    def __str__(self):
        return f"Compra #{self.pk}"

    @property
    def esta_anulada(self):
        return self.estado == self.ESTADO_ANULADA

    @property
    def esta_pendiente(self):
        return self.estado_pago == self.PAGO_PENDIENTE


class DetalleCompra(models.Model):
    TIPO_REVENTA = "reventa"
    TIPO_INSUMO = "insumo"
    TIPO_OTRO = "otro"
    TIPOS = [
        (TIPO_REVENTA, "Producto para la venta"),
        (TIPO_INSUMO, "Insumo de producción"),
        (TIPO_OTRO, "Materiales y otros"),
    ]

    compra = models.ForeignKey(Compra, on_delete=models.PROTECT, related_name="detalles")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, null=True, blank=True)
    descripcion = models.CharField("descripción", max_length=150)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad_medida = models.CharField("unidad de medida", max_length=5, blank=True)
    costo_unitario = models.DecimalField("costo unitario", max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "detalle de compra"
        verbose_name_plural = "detalles de compra"
        constraints = [
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="detalle_compra_cantidad_positiva"),
            models.CheckConstraint(condition=Q(subtotal__gt=0), name="detalle_compra_subtotal_positivo"),
            models.CheckConstraint(
                condition=(
                    Q(tipo="reventa", producto__isnull=False, insumo__isnull=True)
                    | Q(tipo="insumo", producto__isnull=True, insumo__isnull=False)
                    | Q(tipo="otro", producto__isnull=True, insumo__isnull=True)
                ),
                name="detalle_compra_tipo_coherente",
            ),
        ]

    def __str__(self):
        return self.descripcion
