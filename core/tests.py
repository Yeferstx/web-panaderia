from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario


class PruebasInicio(TestCase):
    def test_inicio_pide_sesion(self):
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(respuesta.status_code, 302)

    def test_inicio_con_sesion(self):
        empleado = Usuario.objects.create_user("cajera", password="ClaveSegura2026")
        empleado.groups.add(Group.objects.get(name="Empleado"))
        self.client.force_login(empleado)
        respuesta = self.client.get(reverse("inicio"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Empleado")
