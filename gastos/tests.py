import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from compras.models import Compra
from productos.models import Categoria, Producto
from usuarios.models import Usuario
from ventas.models import Venta

from . import servicios
from .models import CategoriaGasto, CierreCaja, Gasto, MovimientoCaja


def crear_usuario(nombre, grupo):
    usuario = Usuario.objects.create_user(nombre, password="ClaveSegura2026")
    usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


class PruebasGastos(TestCase):
    def setUp(self):
        self.administrador = crear_usuario("dueno", "Administrador")
        self.empleado = crear_usuario("cajera", "Empleado")
        self.servicios_publicos = CategoriaGasto.objects.get(nombre="Servicios públicos")
        self.client.force_login(self.administrador)

    def registrar_gasto(self, valor="85.000", metodo="efectivo", codigo=None):
        return self.client.post(reverse("gastos:nuevo"), {
            "codigo_operacion": str(codigo or uuid.uuid4()),
            "fecha": timezone.localdate().isoformat(),
            "categoria": self.servicios_publicos.pk,
            "descripcion": "Recibo de la luz",
            "valor": valor,
            "metodo_pago": metodo,
            "observaciones": "",
        }, follow=True)

    def test_categorias_iniciales(self):
        self.assertEqual(CategoriaGasto.objects.count(), 5)

    def test_registrar_gasto(self):
        respuesta = self.registrar_gasto()
        gasto = Gasto.objects.get()
        self.assertEqual(gasto.valor, Decimal("85000"))
        self.assertEqual(gasto.usuario, self.administrador)
        self.assertContains(respuesta, "guardado por $85.000")

    def test_gasto_no_acepta_cero(self):
        self.registrar_gasto(valor="0")
        self.assertFalse(Gasto.objects.exists())

    def test_doble_envio_un_solo_gasto(self):
        codigo = uuid.uuid4()
        self.registrar_gasto(codigo=codigo)
        self.registrar_gasto(codigo=codigo)
        self.assertEqual(Gasto.objects.count(), 1)

    def test_anular_gasto(self):
        self.registrar_gasto()
        gasto = Gasto.objects.get()
        self.client.post(reverse("gastos:anular", args=[gasto.pk]), {"motivo": "Se registró mal"})
        gasto.refresh_from_db()
        self.assertTrue(gasto.esta_anulado)

        respuesta = self.client.get(reverse("gastos:lista"))
        self.assertEqual(respuesta.context["total"], 0)

    def test_empleado_no_entra(self):
        self.client.force_login(self.empleado)
        for url in [reverse("gastos:lista"), reverse("gastos:nuevo"), reverse("gastos:caja")]:
            self.assertEqual(self.client.get(url).status_code, 403, url)


class PruebasCaja(TestCase):
    def setUp(self):
        self.administrador = crear_usuario("dueno", "Administrador")
        self.hoy = timezone.localdate()
        categoria = Categoria.objects.create(nombre="Panes")
        Producto.objects.create(nombre="Pan", categoria=categoria, precio_venta=500)

        Venta.objects.create(usuario=self.administrador, total=20000, metodo_pago="efectivo")
        Venta.objects.create(usuario=self.administrador, total=7000, metodo_pago="transferencia")
        Venta.objects.create(usuario=self.administrador, total=3000, metodo_pago="efectivo", estado="anulada")

        categoria_gasto = CategoriaGasto.objects.first()
        Gasto.objects.create(
            usuario=self.administrador, categoria=categoria_gasto, descripcion="Transporte",
            valor=4000, metodo_pago="efectivo",
        )
        Compra.objects.create(
            usuario=self.administrador, total=10000, estado_pago="pagada",
            metodo_pago="efectivo", fecha_pago=self.hoy,
        )
        Compra.objects.create(usuario=self.administrador, total=50000, estado_pago="pendiente")
        MovimientoCaja.objects.create(usuario=self.administrador, tipo="retiro", valor=2000, motivo="Retiro del dueño")
        self.client.force_login(self.administrador)

    def test_calculo_del_efectivo_esperado(self):
        resumen = servicios.calcular_caja(self.hoy, Decimal("50000"))
        self.assertEqual(resumen["ventas_efectivo"], 20000)
        self.assertEqual(resumen["ventas_otros_medios"], 7000)
        self.assertEqual(resumen["gastos_efectivo"], 4000)
        self.assertEqual(resumen["compras_efectivo"], 10000)
        self.assertEqual(resumen["salidas"], 2000)
        self.assertEqual(resumen["efectivo_esperado"], 50000 + 20000 - 4000 - 10000 - 2000)

    def test_cerrar_caja_con_diferencia(self):
        self.client.post(reverse("gastos:cerrar_caja"), {
            "fecha": self.hoy.isoformat(),
            "saldo_inicial": "50.000",
            "efectivo_contado": "53.000",
            "observaciones": "",
        })
        cierre = CierreCaja.objects.get()
        self.assertEqual(cierre.efectivo_esperado, Decimal("54000"))
        self.assertEqual(cierre.diferencia, Decimal("-1000"))

        respuesta = self.client.get(reverse("gastos:caja"))
        self.assertContains(respuesta, "Faltaron $1.000")

    def test_no_se_cierra_dos_veces(self):
        datos = {"fecha": self.hoy.isoformat(), "saldo_inicial": "0", "efectivo_contado": "0", "observaciones": ""}
        self.client.post(reverse("gastos:cerrar_caja"), datos)
        respuesta = self.client.post(reverse("gastos:cerrar_caja"), datos, follow=True)
        self.assertEqual(CierreCaja.objects.count(), 1)
        self.assertContains(respuesta, "ya está cerrada")

    def test_saldo_inicial_sugerido_es_el_cierre_anterior(self):
        ayer = self.hoy - timedelta(days=1)
        CierreCaja.objects.create(
            fecha=ayer, saldo_inicial=0, ventas_efectivo=0, gastos_efectivo=0, compras_efectivo=0,
            entradas=0, salidas=0, efectivo_esperado=0, efectivo_contado=35000, diferencia=35000,
            usuario=self.administrador,
        )
        self.assertEqual(servicios.saldo_inicial_sugerido(self.hoy), Decimal("35000"))

    def test_no_se_agregan_movimientos_en_caja_cerrada(self):
        self.client.post(reverse("gastos:cerrar_caja"), {
            "fecha": self.hoy.isoformat(), "saldo_inicial": "0", "efectivo_contado": "0", "observaciones": "",
        })
        self.client.post(reverse("gastos:movimiento_caja"), {
            "fecha": self.hoy.isoformat(), "tipo": "ingreso", "valor": "5000", "motivo": "Sencillo",
        })
        self.assertEqual(MovimientoCaja.objects.count(), 1)

    def test_compra_pendiente_no_resta(self):
        resumen = servicios.calcular_caja(self.hoy, 0)
        self.assertEqual(resumen["compras_efectivo"], 10000)
