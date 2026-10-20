from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from compras.models import Compra, DetalleCompra
from gastos.models import CategoriaGasto, Gasto
from inventario.models import Insumo
from produccion.models import ConsumoPreparacion, Preparacion
from productos.models import Categoria, Producto
from usuarios.models import Usuario
from ventas.models import DetalleVenta, Venta

from . import servicios


def crear_usuario(nombre, grupo):
    usuario = Usuario.objects.create_user(nombre, password="ClaveSegura2026")
    usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


class PruebasRangos(TestCase):
    def test_rango_semanal_va_de_lunes_a_domingo(self):
        miercoles = date(2026, 10, 21)
        self.assertEqual(servicios.calcular_rango("semanal", miercoles), (date(2026, 10, 19), date(2026, 10, 25)))

    def test_rango_mensual(self):
        self.assertEqual(servicios.calcular_rango("mensual", date(2026, 2, 10)), (date(2026, 2, 1), date(2026, 2, 28)))

    def test_navegacion(self):
        self.assertEqual(servicios.fecha_anterior("mensual", date(2026, 3, 15)), date(2026, 2, 28))
        self.assertEqual(servicios.fecha_siguiente("semanal", date(2026, 10, 21)), date(2026, 10, 26))


class PruebasInforme(TestCase):
    def setUp(self):
        self.administrador = crear_usuario("dueno", "Administrador")
        self.empleado = crear_usuario("cajera", "Empleado")
        self.hoy = timezone.localdate()

        bebidas = Categoria.objects.create(nombre="Bebidas")
        panes = Categoria.objects.create(nombre="Panes")
        self.gaseosa = Producto.objects.create(
            nombre="Gaseosa", categoria=bebidas, precio_venta=3000, control_inventario="unidades"
        )
        self.pan = Producto.objects.create(
            nombre="Pan por importe", categoria=panes, forma_venta="importe", control_inventario="produccion"
        )
        self.harina = Insumo.objects.create(nombre="Harina", unidad_medida="kg")

        compra = Compra.objects.create(
            usuario=self.administrador, total=100000, estado_pago="pagada",
            metodo_pago="efectivo", fecha_pago=self.hoy,
        )
        DetalleCompra.objects.create(
            compra=compra, tipo="reventa", producto=self.gaseosa, descripcion="Gaseosa",
            cantidad=20, costo_unitario=2000, subtotal=40000,
        )
        DetalleCompra.objects.create(
            compra=compra, tipo="insumo", insumo=self.harina, descripcion="Harina",
            cantidad=20, costo_unitario=3000, subtotal=60000,
        )

        venta = Venta.objects.create(usuario=self.empleado, total=14000, metodo_pago="efectivo")
        DetalleVenta.objects.create(
            venta=venta, producto=self.gaseosa, nombre_producto="Gaseosa",
            cantidad=3, precio_unitario=3000, subtotal=9000,
        )
        DetalleVenta.objects.create(venta=venta, producto=self.pan, nombre_producto="Pan por importe", subtotal=5000)
        Venta.objects.create(usuario=self.empleado, total=50000, metodo_pago="efectivo", estado="anulada")
        Venta.objects.create(usuario=self.empleado, total=6000, metodo_pago="transferencia")

        Gasto.objects.create(
            usuario=self.administrador, categoria=CategoriaGasto.objects.first(),
            descripcion="Luz", valor=8000, metodo_pago="efectivo",
        )

        preparacion = Preparacion.objects.create(usuario=self.empleado, nombre="Pan blandito", bandejas=4)
        ConsumoPreparacion.objects.create(preparacion=preparacion, insumo=self.harina, cantidad=2)

        self.client.force_login(self.administrador)

    def test_ventas_sin_anuladas(self):
        informe = servicios.armar_informe("diario", self.hoy)
        self.assertEqual(informe["ventas"]["total"], 20000)
        self.assertEqual(informe["ventas"]["cantidad"], 2)
        metodos = {m["nombre"]: m["total"] for m in informe["ventas"]["por_metodo"]}
        self.assertEqual(metodos["Efectivo"], 14000)
        self.assertEqual(metodos["Transferencia"], 6000)

    def test_compras_no_se_cuentan_como_gastos(self):
        informe = servicios.armar_informe("mensual", self.hoy)
        self.assertEqual(informe["gastos"]["total"], 8000)
        self.assertEqual(informe["compras"]["total"], 100000)
        self.assertEqual(informe["flujo"]["salidas"]["gastos"], 8000)
        self.assertEqual(informe["flujo"]["salidas"]["compras"], 100000)

    def test_resultado_preliminar(self):
        informe = servicios.armar_informe("diario", self.hoy)
        resultado = informe["resultado"]
        self.assertEqual(resultado["costo_reventa"], 6000)
        self.assertEqual(resultado["costo_insumos"], 6000)
        self.assertEqual(resultado["resultado"], 20000 - 6000 - 6000 - 8000)

    def test_resultado_avisa_lo_que_falta(self):
        ConsumoPreparacion.objects.all().delete()
        Preparacion.objects.all().delete()
        informe = servicios.armar_informe("diario", self.hoy)
        self.assertTrue(any("insumos usados" in texto for texto in informe["resultado"]["faltantes"]))

    def test_productos_vendidos_y_por_importe(self):
        informe = servicios.armar_informe("semanal", self.hoy)
        self.assertEqual(informe["vendidos"][0]["nombre"], "Gaseosa")
        self.assertEqual(informe["vendidos"][0]["cantidad"], Decimal("3"))
        self.assertEqual(informe["por_importe"][0]["total"], Decimal("5000"))

    def test_ventas_por_dia_cubre_toda_la_semana(self):
        informe = servicios.armar_informe("semanal", self.hoy)
        self.assertEqual(len(informe["por_dia"]), 7)
        dia_hoy = [d for d in informe["por_dia"] if d["fecha"] == self.hoy][0]
        self.assertEqual(dia_hoy["total"], 20000)
        self.assertEqual(dia_hoy["porcentaje"], 100)

    def test_produccion(self):
        informe = servicios.armar_informe("mensual", self.hoy)
        self.assertEqual(informe["produccion"]["cantidad"], 1)
        self.assertEqual(informe["produccion"]["bandejas"], Decimal("4"))

    def test_otro_dia_no_mezcla_datos(self):
        informe = servicios.armar_informe("diario", self.hoy - timedelta(days=1))
        self.assertEqual(informe["ventas"]["total"], 0)
        self.assertEqual(informe["gastos"]["total"], 0)

    def test_pantallas_de_informe(self):
        for tipo in ["diario", "semanal", "mensual"]:
            respuesta = self.client.get(reverse("reportes:informe"), {"tipo": tipo})
            self.assertEqual(respuesta.status_code, 200)
            self.assertContains(respuesta, "Resultado preliminar")
        respuesta = self.client.get(reverse("reportes:informe"), {"tipo": "otro", "fecha": "no-es-fecha"})
        self.assertEqual(respuesta.status_code, 200)

    def test_empleado_no_ve_informes(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse("reportes:informe")).status_code, 403)

    def test_inicio_con_datos_reales(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(respuesta.context["ventas_hoy"]["total"], 20000)
        self.assertEqual(respuesta.context["gastos_hoy"], 8000)
        self.assertContains(respuesta, "$20.000")

    def test_inicio_del_empleado(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(respuesta.context["mis_ventas_total"], 20000)
        self.assertNotContains(respuesta, "Compras del mes")
