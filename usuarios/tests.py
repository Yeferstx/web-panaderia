from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import Usuario
from .permisos import es_administrador


class PruebasUsuarios(TestCase):
    def setUp(self):
        self.administrador = Usuario.objects.create_user("dueno", password="ClaveSegura2026")
        self.administrador.groups.add(Group.objects.get(name="Administrador"))
        self.empleado = Usuario.objects.create_user("cajera", password="ClaveSegura2026")
        self.empleado.groups.add(Group.objects.get(name="Empleado"))

    def test_existen_los_grupos(self):
        self.assertTrue(Group.objects.filter(name="Administrador").exists())
        self.assertTrue(Group.objects.filter(name="Empleado").exists())

    def test_roles(self):
        self.assertTrue(es_administrador(self.administrador))
        self.assertFalse(es_administrador(self.empleado))

    def test_contrasena_no_se_guarda_en_texto_plano(self):
        self.assertNotEqual(self.empleado.password, "ClaveSegura2026")
        self.assertTrue(self.empleado.check_password("ClaveSegura2026"))

    def test_ingresar_y_salir(self):
        respuesta = self.client.post(
            reverse("login"),
            {"username": "cajera", "password": "ClaveSegura2026"},
        )
        self.assertRedirects(respuesta, reverse("inicio"))

        respuesta = self.client.post(reverse("logout"))
        self.assertRedirects(respuesta, reverse("login"))

        respuesta = self.client.get(reverse("inicio"))
        self.assertRedirects(respuesta, reverse("login") + "?next=/")

    def test_contrasena_incorrecta(self):
        respuesta = self.client.post(
            reverse("login"),
            {"username": "cajera", "password": "otra"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Usuario o contraseña incorrectos")
