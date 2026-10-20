from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from core.models import RegistroActividad
from inventario.models import MovimientoInventario
from usuarios.models import Usuario

from .models import Categoria, Producto


def crear_usuario(nombre, grupo):
    usuario = Usuario.objects.create_user(nombre, password="ClaveSegura2026")
    usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


class PruebasProductos(TestCase):
    def setUp(self):
        self.administrador = crear_usuario("dueno", "Administrador")
        self.empleado = crear_usuario("cajera", "Empleado")
        self.bebidas = Categoria.objects.create(nombre="Bebidas")
        self.client.force_login(self.administrador)

    def datos_producto(self, **cambios):
        datos = {
            "nombre": "Coca-Cola personal",
            "categoria": self.bebidas.pk,
            "descripcion": "",
            "forma_venta": "unidad",
            "precio_venta": "3.000",
            "control_inventario": "unidades",
            "unidad_medida": "und",
            "existencia_minima": "6",
            "existencia_inicial": "24",
        }
        datos.update(cambios)
        return datos

    def test_crear_categoria(self):
        respuesta = self.client.post(reverse("productos:categoria_nueva"), {"nombre": "Panes básicos"})
        self.assertRedirects(respuesta, reverse("productos:categorias"))
        self.assertTrue(Categoria.objects.filter(nombre="Panes básicos").exists())

    def test_crear_producto_con_existencia_inicial(self):
        respuesta = self.client.post(reverse("productos:nuevo"), self.datos_producto())
        self.assertRedirects(respuesta, reverse("productos:lista"))

        producto = Producto.objects.get(nombre="Coca-Cola personal")
        self.assertEqual(producto.precio_venta, Decimal("3000"))
        self.assertEqual(producto.existencia, Decimal("24"))

        movimiento = MovimientoInventario.objects.get(producto=producto)
        self.assertEqual(movimiento.tipo, "inicial")
        self.assertEqual(movimiento.cantidad, Decimal("24"))

    def test_producto_por_unidad_necesita_precio(self):
        respuesta = self.client.post(reverse("productos:nuevo"), self.datos_producto(precio_venta=""))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Los productos por unidad necesitan precio")
        self.assertFalse(Producto.objects.exists())

    def test_producto_por_importe_sin_precio(self):
        datos = self.datos_producto(
            nombre="Pan básico por importe",
            forma_venta="importe",
            precio_venta="",
            control_inventario="produccion",
            existencia_inicial="",
        )
        respuesta = self.client.post(reverse("productos:nuevo"), datos)
        self.assertRedirects(respuesta, reverse("productos:lista"))
        producto = Producto.objects.get(nombre="Pan básico por importe")
        self.assertIsNone(producto.precio_venta)

    def test_importe_no_puede_contar_unidades(self):
        datos = self.datos_producto(forma_venta="importe", precio_venta="", existencia_inicial="")
        respuesta = self.client.post(reverse("productos:nuevo"), datos)
        self.assertContains(respuesta, "no puede contar existencias por unidades")

    def test_modificar_precio_queda_registrado(self):
        self.client.post(reverse("productos:nuevo"), self.datos_producto())
        producto = Producto.objects.get(nombre="Coca-Cola personal")

        datos = self.datos_producto(precio_venta="3500")
        del datos["existencia_inicial"]
        self.client.post(reverse("productos:editar", args=[producto.pk]), datos)

        producto.refresh_from_db()
        self.assertEqual(producto.precio_venta, Decimal("3500"))
        registro = RegistroActividad.objects.get(accion="Cambio de precio")
        self.assertIn("$3.000", registro.descripcion)
        self.assertIn("$3.500", registro.descripcion)

    def test_desactivar_producto_conserva_historial(self):
        self.client.post(reverse("productos:nuevo"), self.datos_producto())
        producto = Producto.objects.get(nombre="Coca-Cola personal")

        self.client.post(reverse("productos:estado", args=[producto.pk]))

        producto.refresh_from_db()
        self.assertFalse(producto.activo)
        self.assertEqual(producto.movimientos.count(), 1)

    def test_no_se_cambia_control_si_hay_existencias(self):
        self.client.post(reverse("productos:nuevo"), self.datos_producto())
        producto = Producto.objects.get(nombre="Coca-Cola personal")

        datos = self.datos_producto(control_inventario="ninguno")
        del datos["existencia_inicial"]
        respuesta = self.client.post(reverse("productos:editar", args=[producto.pk]), datos)
        self.assertContains(respuesta, "Ajústelas a 0")

    def test_base_de_datos_rechaza_precio_negativo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Producto.objects.create(nombre="Malo", categoria=self.bebidas, precio_venta=-100)

    def test_empleado_no_entra_a_productos(self):
        self.client.force_login(self.empleado)
        urls = [
            reverse("productos:lista"),
            reverse("productos:nuevo"),
            reverse("productos:categorias"),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)


class PruebasCatalogo(TestCase):
    def test_cargar_catalogo(self):
        call_command("cargar_catalogo_prueba", stdout=StringIO())

        self.assertEqual(Categoria.objects.count(), 5)
        self.assertEqual(Producto.objects.count(), 22)
        self.assertEqual(Producto.objects.get(nombre="Empanada").precio_venta, Decimal("2500"))

        por_importe = Producto.objects.filter(forma_venta="importe")
        self.assertEqual(
            set(por_importe.values_list("nombre", flat=True)),
            {"Pan básico por importe", "Pan especial por importe"},
        )

        for prohibido in ["Cuca", "Pandebono", "Almojábana", "Roscón", "Palito de queso", "Chocolate"]:
            self.assertFalse(Producto.objects.filter(nombre__icontains=prohibido).exists())

    def test_cargar_dos_veces_no_duplica_ni_cambia_precios(self):
        call_command("cargar_catalogo_prueba", stdout=StringIO())
        Producto.objects.filter(nombre="Tinto").update(precio_venta=1200)

        call_command("cargar_catalogo_prueba", stdout=StringIO())

        self.assertEqual(Producto.objects.count(), 22)
        self.assertEqual(Producto.objects.get(nombre="Tinto").precio_venta, Decimal("1200"))
