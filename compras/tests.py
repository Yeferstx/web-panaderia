import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventario.models import Insumo, MovimientoInventario
from productos.models import Categoria, Producto
from usuarios.models import Usuario

from .models import Compra, DetalleCompra


def crear_usuario(nombre, grupo):
    usuario = Usuario.objects.create_user(nombre, password="ClaveSegura2026")
    usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


class PruebasCompras(TestCase):
    def setUp(self):
        self.administrador = crear_usuario("dueno", "Administrador")
        self.empleado = crear_usuario("cajera", "Empleado")
        self.harina = Insumo.objects.create(nombre="Harina", unidad_medida="kg")
        bebidas = Categoria.objects.create(nombre="Bebidas")
        self.gaseosa = Producto.objects.create(
            nombre="Gaseosa personal", categoria=bebidas, precio_venta=2500, control_inventario="unidades"
        )
        self.client.force_login(self.administrador)

    def comprar(self, lineas, estado_pago="pagada", metodo="efectivo", codigo=None, fecha=None):
        datos = {
            "codigo_operacion": str(codigo or uuid.uuid4()),
            "fecha": (fecha or timezone.localdate()).isoformat(),
            "proveedor": "",
            "estado_pago": estado_pago,
            "metodo_pago": metodo,
            "observaciones": "",
            "lineas-TOTAL_FORMS": str(len(lineas)),
            "lineas-INITIAL_FORMS": "0",
            "lineas-MIN_NUM_FORMS": "0",
            "lineas-MAX_NUM_FORMS": "50",
        }
        for numero, linea in enumerate(lineas):
            for campo, valor in linea.items():
                datos[f"lineas-{numero}-{campo}"] = valor
        return self.client.post(reverse("compras:nueva"), datos, follow=True)

    def linea_harina(self, cantidad="20", valor="80000"):
        return {"articulo": f"insumo-{self.harina.pk}", "descripcion": "", "cantidad": cantidad, "valor": valor}

    def test_compra_de_20_kg_de_harina_suma_inventario(self):
        self.comprar([self.linea_harina()])

        compra = Compra.objects.get()
        self.assertEqual(compra.total, Decimal("80000"))
        detalle = compra.detalles.get()
        self.assertEqual(detalle.tipo, "insumo")
        self.assertEqual(detalle.costo_unitario, Decimal("4000"))
        self.assertEqual(detalle.unidad_medida, "kg")

        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("20"))

    def test_compra_con_varias_lineas(self):
        self.comprar([
            self.linea_harina(),
            {"articulo": f"producto-{self.gaseosa.pk}", "descripcion": "", "cantidad": "24", "valor": "36.000"},
            {"articulo": "otro", "descripcion": "Bolsas de papel", "cantidad": "100", "valor": "15000"},
        ])
        compra = Compra.objects.get()
        self.assertEqual(compra.total, Decimal("131000"))
        self.assertEqual(compra.detalles.count(), 3)

        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.existencia, Decimal("24"))
        otro = compra.detalles.get(tipo="otro")
        self.assertEqual(otro.descripcion, "Bolsas de papel")
        self.assertEqual(MovimientoInventario.objects.filter(origen="compra").count(), 2)

    def test_otro_necesita_descripcion(self):
        respuesta = self.comprar([{"articulo": "otro", "descripcion": "", "cantidad": "1", "valor": "5000"}])
        self.assertContains(respuesta, "Escriba qué se compró")
        self.assertFalse(Compra.objects.exists())

    def test_compra_sin_lineas(self):
        respuesta = self.comprar([{"articulo": "", "descripcion": "", "cantidad": "", "valor": ""}])
        self.assertContains(respuesta, "Agregue al menos un artículo")
        self.assertFalse(Compra.objects.exists())

    def test_pagada_necesita_metodo(self):
        respuesta = self.comprar([self.linea_harina()], metodo="")
        self.assertContains(respuesta, "Elija cómo se pagó")
        self.assertFalse(Compra.objects.exists())

    def test_fecha_futura_no_se_permite(self):
        self.comprar([self.linea_harina()], fecha=timezone.localdate() + timedelta(days=1))
        self.assertFalse(Compra.objects.exists())

    def test_compra_pendiente_y_pago_posterior(self):
        self.comprar([self.linea_harina()], estado_pago="pendiente", metodo="efectivo")
        compra = Compra.objects.get()
        self.assertTrue(compra.esta_pendiente)
        self.assertEqual(compra.metodo_pago, "")
        self.assertIsNone(compra.fecha_pago)

        self.client.post(reverse("compras:pagar", args=[compra.pk]), {
            "metodo_pago": "transferencia",
            "fecha_pago": timezone.localdate().isoformat(),
        })
        compra.refresh_from_db()
        self.assertFalse(compra.esta_pendiente)
        self.assertEqual(compra.metodo_pago, "transferencia")

    def test_doble_envio_guarda_una_sola_compra(self):
        codigo = uuid.uuid4()
        self.comprar([self.linea_harina()], codigo=codigo)
        self.comprar([self.linea_harina()], codigo=codigo)
        self.assertEqual(Compra.objects.count(), 1)
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("20"))

    def test_falla_no_deja_compra_parcial(self):
        with patch("compras.servicios.registrar_movimiento", side_effect=Exception("falla simulada")):
            with self.assertRaises(Exception):
                self.comprar([self.linea_harina()])
        self.assertFalse(Compra.objects.exists())
        self.assertFalse(DetalleCompra.objects.exists())
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("0"))

    def test_anular_revierte_inventario_sin_borrar(self):
        self.comprar([self.linea_harina()])
        compra = Compra.objects.get()

        self.client.post(reverse("compras:anular", args=[compra.pk]), {"motivo": "Error de registro"})
        self.client.post(reverse("compras:anular", args=[compra.pk]), {"motivo": "Otra vez"})

        compra.refresh_from_db()
        self.assertTrue(compra.esta_anulada)
        self.assertEqual(compra.detalles.count(), 1)
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("0"))
        self.assertEqual(MovimientoInventario.objects.filter(tipo="anulacion").count(), 1)

    def test_empleado_no_entra_a_compras(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse("compras:lista")).status_code, 403)
        self.assertEqual(self.client.get(reverse("compras:nueva")).status_code, 403)

    def test_pantallas_cargan(self):
        self.comprar([self.linea_harina()])
        compra = Compra.objects.get()
        for url in [
            reverse("compras:lista"),
            reverse("compras:nueva"),
            reverse("compras:detalle", args=[compra.pk]),
            reverse("compras:proveedores"),
            reverse("compras:proveedor_nuevo"),
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
