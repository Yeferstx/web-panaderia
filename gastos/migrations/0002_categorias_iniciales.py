from django.db import migrations

CATEGORIAS = ["Servicios públicos", "Arriendo", "Transporte", "Mantenimiento", "Otros"]


def crear_categorias(apps, schema_editor):
    CategoriaGasto = apps.get_model("gastos", "CategoriaGasto")
    for nombre in CATEGORIAS:
        CategoriaGasto.objects.get_or_create(nombre=nombre)


def borrar_categorias(apps, schema_editor):
    CategoriaGasto = apps.get_model("gastos", "CategoriaGasto")
    CategoriaGasto.objects.filter(nombre__in=CATEGORIAS, gasto__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gastos", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_categorias, borrar_categorias),
    ]
