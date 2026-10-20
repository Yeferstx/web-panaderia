from django.core.management.base import BaseCommand
from django.db import transaction

from productos.models import Categoria, Producto

UNIDAD = Producto.FORMA_UNIDAD
IMPORTE = Producto.FORMA_IMPORTE
CONTAR = Producto.CONTROL_UNIDADES
PRODUCCION = Producto.CONTROL_PRODUCCION
NINGUNO = Producto.CONTROL_NINGUNO

CATALOGO = {
    "Panes básicos": [
        ("Pan rollito", 500, UNIDAD, PRODUCCION),
        ("Pan blandito", 500, UNIDAD, PRODUCCION),
        ("Pan básico", 1000, UNIDAD, PRODUCCION),
        ("Pan básico por importe", None, IMPORTE, PRODUCCION),
    ],
    "Panes especiales": [
        ("Pan de bocadillo", 1500, UNIDAD, PRODUCCION),
        ("Pan de queso", 2000, UNIDAD, PRODUCCION),
        ("Pan de la abuela", 2500, UNIDAD, PRODUCCION),
        ("Pan especial por importe", None, IMPORTE, PRODUCCION),
    ],
    "Hojaldres y otros productos": [
        ("Hojaldra", 1500, UNIDAD, PRODUCCION),
        ("Mantecada", 2500, UNIDAD, PRODUCCION),
        ("Empanada", 2500, UNIDAD, PRODUCCION),
        ("Pastel de pollo", 3500, UNIDAD, PRODUCCION),
        ("Galletas de la panadería", 1000, UNIDAD, PRODUCCION),
    ],
    "Gaseosas y bebidas frías": [
        ("Coca-Cola personal", 3000, UNIDAD, CONTAR),
        ("Gaseosa personal otras marcas", 2500, UNIDAD, CONTAR),
        ("Gaseosa 1,25 litros", 5000, UNIDAD, CONTAR),
        ("Gaseosa 3 litros", 9000, UNIDAD, CONTAR),
        ("Jugo Hit personal", 2500, UNIDAD, CONTAR),
        ("Cifrut grande", 3500, UNIDAD, CONTAR),
        ("Agua embotellada", 2000, UNIDAD, CONTAR),
    ],
    "Bebidas calientes": [
        ("Tinto", 1000, UNIDAD, NINGUNO),
        ("Café con leche", 2000, UNIDAD, NINGUNO),
    ],
}


class Command(BaseCommand):
    help = "Carga el catálogo de prueba. Los precios son de prueba y se pueden editar."

    @transaction.atomic
    def handle(self, *args, **opciones):
        creados = 0
        existentes = 0

        for nombre_categoria, productos in CATALOGO.items():
            categoria, _ = Categoria.objects.get_or_create(nombre=nombre_categoria)

            for nombre, precio, forma, control in productos:
                _, creado = Producto.objects.get_or_create(
                    nombre=nombre,
                    defaults={
                        "categoria": categoria,
                        "precio_venta": precio,
                        "forma_venta": forma,
                        "control_inventario": control,
                    },
                )
                if creado:
                    creados += 1
                else:
                    existentes += 1

        self.stdout.write(self.style.SUCCESS(f"Productos creados: {creados}. Ya existían: {existentes}."))
        if existentes:
            self.stdout.write("Los productos que ya existían no se modificaron.")
