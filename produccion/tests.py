import uuid
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventario.models import Insumo, MovimientoInventario
from inventario.servicios import registrar_movimiento
from usuarios.models import Usuario

from .models import ConsumoPreparacion, Preparacion


def crear_usuario(nombre, grupo):
    usuario = Usuario.objects.create_user(nombre, password="ClaveSegura2026")
    usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


class PruebasProduccion(TestCase):
    def setUp(self):
        self.administrador = crear_usuario("dueno", "Administrador")
        self.empleado = crear_usuario("panadero", "Empleado")
        self.harina = Insumo.objects.create(nombre="Harina", unidad_medida="kg")
        self.azucar = Insumo.objects.create(nombre="Azúcar", unidad_medida="kg")
        registrar_movimiento(self.harina, "inicial", Decimal("30"), "Existencia inicial", self.administrador)
        self.client.force_login(self.empleado)

    def registrar(self, consumos=None, codigo=None, **resultado):
        consumos = consumos or []
        datos = {
            "codigo_operacion": str(codigo or uuid.uuid4()),
            "fecha": timezone.localdate().isoformat(),
            "nombre": "Pan blandito",
            "producto": "",
            "bandejas": "",
            "unidades_aproximadas": "",
            "unidades_minimas": "",
            "unidades_maximas": "",
            "observaciones": "",
            "consumos-TOTAL_FORMS": str(max(len(consumos), 1)),
            "consumos-INITIAL_FORMS": "0",
            "consumos-MIN_NUM_FORMS": "0",
            "consumos-MAX_NUM_FORMS": "30",
        }
        datos.update(resultado)
        for numero, consumo in enumerate(consumos):
            datos[f"consumos-{numero}-insumo"] = consumo[0].pk
            datos[f"consumos-{numero}-cantidad"] = consumo[1]
        return self.client.post(reverse("produccion:nueva"), datos, follow=True)

    def test_cuatro_bandejas_sin_unidades(self):
        respuesta = self.registrar(consumos=[(self.harina, "20")], bandejas="4")

        preparacion = Preparacion.objects.get()
        self.assertEqual(preparacion.bandejas, Decimal("4"))
        self.assertIsNone(preparacion.unidades_aproximadas)
        self.assertIsNone(preparacion.unidades_minimas)
        self.assertEqual(preparacion.usuario, self.empleado)
        self.assertContains(respuesta, "4 bandejas")

        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("10"))

    def test_ejemplo_harina_completo(self):
        registrar_movimiento(self.harina, "entrada", Decimal("20"), "Compra", self.administrador)
        self.registrar(consumos=[(self.harina, "15")], bandejas="3")
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("35"))

    def test_sin_insumos_ni_unidades(self):
        self.registrar(bandejas="2")
        preparacion = Preparacion.objects.get()
        self.assertFalse(preparacion.consumos.exists())

    def test_intervalo_de_unidades(self):
        self.registrar(unidades_minimas="80", unidades_maximas="100")
        preparacion = Preparacion.objects.get()
        self.assertEqual(preparacion.unidades_minimas, 80)
        self.assertEqual(preparacion.unidades_maximas, 100)

    def test_intervalo_invertido_se_rechaza(self):
        respuesta = self.registrar(unidades_minimas="100", unidades_maximas="80")
        self.assertContains(respuesta, "mayor o igual")
        self.assertFalse(Preparacion.objects.exists())

    def test_mismo_insumo_dos_veces_se_suma(self):
        self.registrar(consumos=[(self.harina, "5"), (self.harina, "2,5")], bandejas="1")
        consumo = ConsumoPreparacion.objects.get()
        self.assertEqual(consumo.cantidad, Decimal("7.5"))

    def test_insumo_sin_existencia_avisa(self):
        respuesta = self.registrar(consumos=[(self.azucar, "2")], bandejas="1")
        self.assertContains(respuesta, "quedó en -2 kg")
        self.azucar.refresh_from_db()
        self.assertEqual(self.azucar.existencia, Decimal("-2"))

    def test_doble_envio(self):
        codigo = uuid.uuid4()
        self.registrar(consumos=[(self.harina, "5")], codigo=codigo, bandejas="1")
        self.registrar(consumos=[(self.harina, "5")], codigo=codigo, bandejas="1")
        self.assertEqual(Preparacion.objects.count(), 1)
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("25"))

    def test_empleado_no_anula_y_administrador_si(self):
        self.registrar(consumos=[(self.harina, "10")], bandejas="2")
        preparacion = Preparacion.objects.get()

        respuesta = self.client.post(reverse("produccion:anular", args=[preparacion.pk]), {"motivo": "x"})
        self.assertEqual(respuesta.status_code, 403)

        self.client.force_login(self.administrador)
        self.client.post(reverse("produccion:anular", args=[preparacion.pk]), {"motivo": "Error"})
        preparacion.refresh_from_db()
        self.assertTrue(preparacion.esta_anulada)
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.existencia, Decimal("30"))
        self.assertEqual(MovimientoInventario.objects.filter(tipo="anulacion").count(), 1)

    def test_pantallas_cargan(self):
        self.registrar(bandejas="1")
        preparacion = Preparacion.objects.get()
        for url in [
            reverse("produccion:lista"),
            reverse("produccion:nueva"),
            reverse("produccion:detalle", args=[preparacion.pk]),
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
