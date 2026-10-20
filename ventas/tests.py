import json
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from inventario.models import MovimientoInventario
from inventario.servicios import registrar_movimiento
from productos.models import Categoria, Producto
from usuarios.models import Usuario

from .models import DetalleVenta, Venta


def crear_usuario(nombre, grupo):
    usuario = Usuario.objects.create_user(nombre, password="ClaveSegura2026")
    usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


class PruebasVentas(TestCase):
    def setUp(self):
        self.administrador = crear_usuario("dueno", "Administrador")
        self.empleado = crear_usuario("cajera", "Empleado")

        panes = Categoria.objects.create(nombre="Panes básicos")
        bebidas = Categoria.objects.create(nombre="Bebidas")
        self.pan_importe = Producto.objects.create(
            nombre="Pan básico por importe", categoria=panes,
            forma_venta="importe", control_inventario="produccion",
        )
        self.empanada = Producto.objects.create(
            nombre="Empanada", categoria=panes, precio_venta=2500, control_inventario="produccion",
        )
        self.gaseosa = Producto.objects.create(
            nombre="Gaseosa personal", categoria=bebidas, precio_venta=3000, control_inventario="unidades",
        )
        registrar_movimiento(self.gaseosa, "inicial", Decimal("10"), "Existencia inicial", self.administrador)

        self.client.force_login(self.empleado)

    def vender(self, lineas, metodo="efectivo", codigo=None):
        return self.client.post(reverse("ventas:nueva"), {
            "lineas": json.dumps(lineas),
            "metodo_pago": metodo,
            "observaciones": "",
            "codigo_operacion": str(codigo or uuid.uuid4()),
        }, follow=True)

    def test_venta_de_5000_de_pan_sin_unidades(self):
        self.vender([{"producto": self.pan_importe.pk, "importe": 5000}])

        venta = Venta.objects.get()
        detalle = venta.detalles.get()
        self.assertEqual(venta.total, Decimal("5000"))
        self.assertEqual(detalle.subtotal, Decimal("5000"))
        self.assertIsNone(detalle.cantidad)
        self.assertIsNone(detalle.precio_unitario)
        self.assertFalse(MovimientoInventario.objects.filter(origen="venta").exists())

    def test_tres_gaseosas_descuentan_inventario(self):
        respuesta = self.vender([{"producto": self.gaseosa.pk, "cantidad": 3}], metodo="transferencia")

        venta = Venta.objects.get()
        self.assertEqual(venta.total, Decimal("9000"))
        self.assertEqual(venta.metodo_pago, "transferencia")
        self.assertContains(respuesta, "guardada por $9.000")

        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.existencia, Decimal("7"))
        movimiento = MovimientoInventario.objects.get(origen="venta", origen_id=venta.pk)
        self.assertEqual(movimiento.cantidad, Decimal("-3"))

    def test_venta_mixta(self):
        self.vender([
            {"producto": self.gaseosa.pk, "cantidad": 2},
            {"producto": self.empanada.pk, "cantidad": 1},
            {"producto": self.pan_importe.pk, "importe": 2000},
        ])
        self.assertEqual(Venta.objects.get().total, Decimal("10500"))
        self.assertEqual(DetalleVenta.objects.count(), 3)

    def test_el_precio_lo_pone_el_servidor(self):
        self.vender([{"producto": self.gaseosa.pk, "cantidad": 1, "precio": 1}])
        self.assertEqual(Venta.objects.get().total, Decimal("3000"))

    def test_precio_historico_no_cambia(self):
        self.vender([{"producto": self.gaseosa.pk, "cantidad": 2}])
        self.gaseosa.precio_venta = 3500
        self.gaseosa.save()

        detalle = DetalleVenta.objects.get()
        self.assertEqual(detalle.precio_unitario, Decimal("3000"))
        self.assertEqual(detalle.subtotal, Decimal("6000"))
        self.assertEqual(detalle.venta.total, Decimal("6000"))

    def test_venta_sin_existencias_avisa_y_queda_en_negativo(self):
        respuesta = self.vender([{"producto": self.gaseosa.pk, "cantidad": 12}])

        self.assertEqual(Venta.objects.count(), 1)
        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.existencia, Decimal("-2"))
        self.assertContains(respuesta, "quedó en -2 en el sistema")

    def test_doble_envio_guarda_una_sola_venta(self):
        codigo = uuid.uuid4()
        self.vender([{"producto": self.gaseosa.pk, "cantidad": 1}], codigo=codigo)
        respuesta = self.vender([{"producto": self.gaseosa.pk, "cantidad": 1}], codigo=codigo)

        self.assertEqual(Venta.objects.count(), 1)
        self.assertContains(respuesta, "ya estaba guardada")
        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.existencia, Decimal("9"))

    def test_falla_no_deja_venta_parcial(self):
        with patch("ventas.servicios.registrar_movimiento", side_effect=Exception("falla simulada")):
            with self.assertRaises(Exception):
                self.vender([
                    {"producto": self.empanada.pk, "cantidad": 1},
                    {"producto": self.gaseosa.pk, "cantidad": 3},
                ])

        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(DetalleVenta.objects.count(), 0)
        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.existencia, Decimal("10"))

    def test_datos_invalidos(self):
        casos = [
            [],
            [{"producto": self.pan_importe.pk, "importe": -5000}],
            [{"producto": self.pan_importe.pk, "importe": 0}],
            [{"producto": self.pan_importe.pk, "importe": "abc"}],
            [{"producto": self.gaseosa.pk, "cantidad": 0}],
            [{"producto": self.gaseosa.pk, "cantidad": -2}],
            [{"producto": self.gaseosa.pk, "cantidad": 1.5}],
            [{"producto": 99999, "cantidad": 1}],
        ]
        for lineas in casos:
            respuesta = self.vender(lineas)
            self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Venta.objects.count(), 0)

    def test_metodo_de_pago_invalido(self):
        self.vender([{"producto": self.empanada.pk, "cantidad": 1}], metodo="fiado")
        self.assertEqual(Venta.objects.count(), 0)

    def test_producto_inactivo_no_se_vende(self):
        self.empanada.activo = False
        self.empanada.save()
        respuesta = self.vender([{"producto": self.empanada.pk, "cantidad": 1}])
        self.assertContains(respuesta, "ya no está disponible")
        self.assertEqual(Venta.objects.count(), 0)

    def test_error_conserva_lo_que_se_habia_agregado(self):
        lineas = [{"producto": self.empanada.pk, "cantidad": 2}]
        respuesta = self.vender(lineas, metodo="")
        self.assertContains(respuesta, "Elija el método de pago")
        self.assertContains(respuesta, '\\"cantidad\\": 2')

    def test_empleado_ve_solo_sus_ventas(self):
        self.vender([{"producto": self.empanada.pk, "cantidad": 1}])
        venta_empleado = Venta.objects.get()

        self.client.force_login(self.administrador)
        self.vender([{"producto": self.empanada.pk, "cantidad": 2}])
        venta_administrador = Venta.objects.exclude(pk=venta_empleado.pk).get()

        self.client.force_login(self.empleado)
        respuesta = self.client.get(reverse("ventas:lista"))
        self.assertContains(respuesta, f"#{venta_empleado.pk}")
        self.assertNotContains(respuesta, f"#{venta_administrador.pk}<")
        self.assertEqual(
            self.client.get(reverse("ventas:detalle", args=[venta_administrador.pk])).status_code, 403
        )

    def test_empleado_no_puede_anular(self):
        self.vender([{"producto": self.gaseosa.pk, "cantidad": 1}])
        venta = Venta.objects.get()
        respuesta = self.client.post(reverse("ventas:anular", args=[venta.pk]), {"motivo": "prueba"})
        self.assertEqual(respuesta.status_code, 403)
        venta.refresh_from_db()
        self.assertFalse(venta.esta_anulada)

    def test_anular_devuelve_existencias_una_sola_vez(self):
        self.vender([{"producto": self.gaseosa.pk, "cantidad": 3}])
        venta = Venta.objects.get()

        self.client.force_login(self.administrador)
        self.client.post(reverse("ventas:anular", args=[venta.pk]), {"motivo": "Se registró dos veces"})
        respuesta = self.client.post(reverse("ventas:anular", args=[venta.pk]), {"motivo": "Otra vez"}, follow=True)

        venta.refresh_from_db()
        self.assertTrue(venta.esta_anulada)
        self.assertEqual(venta.anulada_por, self.administrador)
        self.assertContains(respuesta, "ya estaba anulada")
        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.existencia, Decimal("10"))
        self.assertEqual(MovimientoInventario.objects.filter(tipo="anulacion").count(), 1)

    def test_anulada_no_suma_en_el_total(self):
        self.vender([{"producto": self.empanada.pk, "cantidad": 1}])
        self.vender([{"producto": self.empanada.pk, "cantidad": 2}])
        primera = Venta.objects.order_by("id").first()

        self.client.force_login(self.administrador)
        self.client.post(reverse("ventas:anular", args=[primera.pk]), {"motivo": "Error"})
        respuesta = self.client.get(reverse("ventas:lista"))
        self.assertEqual(respuesta.context["resumen"]["total"], Decimal("5000"))

    def test_pantalla_de_venta_carga(self):
        respuesta = self.client.get(reverse("ventas:nueva"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f'"id": {self.pan_importe.pk}')
        self.assertContains(respuesta, '"por_importe": true')
