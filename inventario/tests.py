from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import RegistroActividad
from productos.models import Categoria, Producto
from usuarios.models import Usuario

from . import servicios
from .models import Insumo, MovimientoInventario


class PruebasInventario(TestCase):
    def setUp(self):
        self.administrador = Usuario.objects.create_user("dueno", password="ClaveSegura2026")
        self.administrador.groups.add(Group.objects.get(name="Administrador"))
        self.empleado = Usuario.objects.create_user("cajera", password="ClaveSegura2026")
        self.empleado.groups.add(Group.objects.get(name="Empleado"))

        bebidas = Categoria.objects.create(nombre="Bebidas")
        panes = Categoria.objects.create(nombre="Panes")
        self.gaseosa = Producto.objects.create(
            nombre="Gaseosa personal", categoria=bebidas, precio_venta=3000, control_inventario="unidades"
        )
        self.pan = Producto.objects.create(
            nombre="Pan de queso", categoria=panes, precio_venta=2000, control_inventario="produccion"
        )
        self.harina = Insumo.objects.create(nombre="Harina", unidad_medida="kg")
        self.client.force_login(self.administrador)

    def test_ejemplo_harina(self):
        servicios.registrar_movimiento(self.harina, "inicial", Decimal("30"), "Existencia inicial", self.administrador)
        servicios.registrar_movimiento(self.harina, "entrada", Decimal("20"), "Compra", self.administrador)
        servicios.registrar_movimiento(self.harina, "salida", Decimal("-15"), "Producción", self.administrador)

        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("35"))
        self.assertEqual(self.harina.movimientos.count(), 3)

    def test_movimiento_guarda_antes_y_despues(self):
        servicios.registrar_movimiento(self.gaseosa, "entrada", Decimal("12"), "Compra", self.administrador)
        movimiento = servicios.registrar_movimiento(self.gaseosa, "salida", Decimal("-3"), "Venta", self.administrador)

        self.assertEqual(movimiento.existencia_anterior, Decimal("12"))
        self.assertEqual(movimiento.existencia_resultante, Decimal("9"))

    def test_existencia_puede_quedar_negativa(self):
        servicios.registrar_movimiento(self.gaseosa, "salida", Decimal("-2"), "Venta", self.administrador)
        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.existencia, Decimal("-2"))
        self.assertEqual(self.gaseosa.estado_existencia, "negativo")

    def test_pan_no_lleva_existencias(self):
        with self.assertRaises(ValidationError):
            servicios.registrar_movimiento(self.pan, "entrada", Decimal("10"), "Prueba", self.administrador)
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_ajuste_registra_la_diferencia(self):
        servicios.registrar_movimiento(self.gaseosa, "entrada", Decimal("12"), "Compra", self.administrador)

        respuesta = self.client.post(
            reverse("inventario:ajustar_producto", args=[self.gaseosa.pk]),
            {"existencia_contada": "10", "motivo": "Conteo físico"},
        )
        self.assertRedirects(respuesta, reverse("inventario:panel"))

        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.existencia, Decimal("10"))
        ajuste = MovimientoInventario.objects.get(tipo="ajuste")
        self.assertEqual(ajuste.cantidad, Decimal("-2"))
        self.assertTrue(RegistroActividad.objects.filter(accion="Ajuste de inventario").exists())

    def test_ajuste_sin_diferencia_se_rechaza(self):
        respuesta = self.client.post(
            reverse("inventario:ajustar_insumo", args=[self.harina.pk]),
            {"existencia_contada": "0", "motivo": "Conteo"},
        )
        self.assertContains(respuesta, "No hay nada que ajustar")
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_ajuste_necesita_motivo(self):
        respuesta = self.client.post(
            reverse("inventario:ajustar_insumo", args=[self.harina.pk]),
            {"existencia_contada": "5", "motivo": ""},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_operacion_fallida_no_deja_cambios(self):
        with patch.object(MovimientoInventario, "save", side_effect=Exception("falla simulada")):
            with self.assertRaises(Exception):
                servicios.registrar_movimiento(self.harina, "entrada", Decimal("20"), "Compra", self.administrador)

        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("0"))
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_crear_insumo_con_coma_decimal(self):
        respuesta = self.client.post(reverse("inventario:insumo_nuevo"), {
            "nombre": "Levadura",
            "unidad_medida": "kg",
            "existencia_minima": "0,5",
            "costo_referencia": "",
            "existencia_inicial": "2,5",
        })
        self.assertRedirects(respuesta, reverse("inventario:panel"))
        levadura = Insumo.objects.get(nombre="Levadura")
        self.assertEqual(levadura.existencia, Decimal("2.5"))
        self.assertEqual(levadura.existencia_minima, Decimal("0.5"))

    def test_no_se_cambia_unidad_con_movimientos(self):
        servicios.registrar_movimiento(self.harina, "entrada", Decimal("20"), "Compra", self.administrador)
        respuesta = self.client.post(reverse("inventario:insumo_editar", args=[self.harina.pk]), {
            "nombre": "Harina",
            "unidad_medida": "g",
            "existencia_minima": "0",
            "costo_referencia": "",
        })
        self.assertContains(respuesta, "No se puede cambiar la unidad")

    def test_alertas(self):
        self.gaseosa.existencia_minima = 6
        self.gaseosa.save()
        servicios.registrar_movimiento(self.gaseosa, "entrada", Decimal("4"), "Compra", self.administrador)
        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.estado_existencia, "bajo")

        respuesta = self.client.get(reverse("inventario:panel"))
        self.assertContains(respuesta, "con existencias bajas")

    def test_historial_y_panel_cargan(self):
        servicios.registrar_movimiento(self.harina, "entrada", Decimal("20"), "Compra", self.administrador)
        self.assertEqual(self.client.get(reverse("inventario:panel")).status_code, 200)
        respuesta = self.client.get(reverse("inventario:movimientos") + f"?insumo={self.harina.pk}")
        self.assertContains(respuesta, "+20 kg")

    def test_empleado_no_entra_a_inventario(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse("inventario:panel")).status_code, 403)
        respuesta = self.client.post(
            reverse("inventario:ajustar_insumo", args=[self.harina.pk]),
            {"existencia_contada": "5", "motivo": "x"},
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(MovimientoInventario.objects.exists())
