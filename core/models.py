from django.conf import settings
from django.db import models


class RegistroActividad(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    accion = models.CharField("acción", max_length=60)
    descripcion = models.TextField("descripción")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "registro de actividad"
        verbose_name_plural = "registros de actividad"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} - {self.usuario} - {self.accion}"
