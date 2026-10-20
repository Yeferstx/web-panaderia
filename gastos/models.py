import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.opciones import METODOS_PAGO


class CategoriaGasto(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "categoría de gasto"
        verbose_name_plural = "categorías de gasto"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Gasto(models.Model):
    ESTADO_CONFIRMADO = "confirmado"
    ESTADO_ANULADO = "anulado"
    ESTADOS = [
        (ESTADO_CONFIRMADO, "Confirmado"),
        (ESTADO_ANULADO, "Anulado"),
    ]

    fecha = models.DateField(default=timezone.localdate)
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.PROTECT, verbose_name="categoría")
    descripcion = models.CharField("descripción", max_length=150)
    valor = models.DecimalField(max_digits=12, decimal_places=0)
    metodo_pago = models.CharField("método de pago", max_length=15, choices=METODOS_PAGO)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="gastos")
    observaciones = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default=ESTADO_CONFIRMADO)
    codigo_operacion = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gastos_anulados",
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.CharField("motivo de anulación", max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "gasto"
        verbose_name_plural = "gastos"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(valor__gt=0), name="gasto_valor_positivo"),
        ]

    def __str__(self):
        return f"{self.descripcion} ({self.fecha:%d/%m/%Y})"

    @property
    def esta_anulado(self):
        return self.estado == self.ESTADO_ANULADO


class MovimientoCaja(models.Model):
    TIPO_INGRESO = "ingreso"
    TIPO_RETIRO = "retiro"
    TIPOS = [
        (TIPO_INGRESO, "Entrada de dinero"),
        (TIPO_RETIRO, "Salida de dinero"),
    ]

    fecha = models.DateField(default=timezone.localdate)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    valor = models.DecimalField(max_digits=12, decimal_places=0)
    motivo = models.CharField(max_length=255)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "movimiento de caja"
        verbose_name_plural = "movimientos de caja"
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(valor__gt=0), name="movimiento_caja_valor_positivo"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.valor}"


class CierreCaja(models.Model):
    fecha = models.DateField(unique=True)
    saldo_inicial = models.DecimalField("efectivo al abrir", max_digits=12, decimal_places=0)
    ventas_efectivo = models.DecimalField(max_digits=12, decimal_places=0)
    gastos_efectivo = models.DecimalField(max_digits=12, decimal_places=0)
    compras_efectivo = models.DecimalField(max_digits=12, decimal_places=0)
    entradas = models.DecimalField(max_digits=12, decimal_places=0)
    salidas = models.DecimalField(max_digits=12, decimal_places=0)
    efectivo_esperado = models.DecimalField(max_digits=12, decimal_places=0)
    efectivo_contado = models.DecimalField(max_digits=12, decimal_places=0)
    diferencia = models.DecimalField(max_digits=12, decimal_places=0)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    observaciones = models.CharField(max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "cierre de caja"
        verbose_name_plural = "cierres de caja"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(condition=Q(saldo_inicial__gte=0), name="cierre_saldo_inicial_no_negativo"),
            models.CheckConstraint(condition=Q(efectivo_contado__gte=0), name="cierre_contado_no_negativo"),
        ]

    def __str__(self):
        return f"Cierre del {self.fecha:%d/%m/%Y}"
