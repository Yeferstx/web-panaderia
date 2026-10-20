from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from usuarios.permisos import solo_administrador

from . import servicios
from .forms import CategoriaForm, ProductoForm
from .models import Categoria, Producto


@solo_administrador
def lista_productos(request):
    buscar = request.GET.get("buscar", "").strip()
    categoria_id = request.GET.get("categoria", "")
    estado = request.GET.get("estado", "activos")

    productos = Producto.objects.select_related("categoria")
    if buscar:
        productos = productos.filter(nombre__icontains=buscar)
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    if estado == "activos":
        productos = productos.filter(activo=True)
    elif estado == "inactivos":
        productos = productos.filter(activo=False)

    return render(request, "productos/lista.html", {
        "productos": productos,
        "categorias": Categoria.objects.all(),
        "buscar": buscar,
        "categoria_id": categoria_id,
        "estado": estado,
    })


@solo_administrador
def crear_producto(request):
    formulario = ProductoForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        producto = servicios.crear_producto(formulario, request.user)
        messages.success(request, f"Producto «{producto.nombre}» guardado.")
        return redirect("productos:lista")
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": "Nuevo producto",
        "volver": "productos:lista",
        "script": "js/productos.js",
    })


@solo_administrador
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    formulario = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and formulario.is_valid():
        servicios.guardar_cambios_producto(formulario, request.user)
        messages.success(request, f"Cambios de «{producto.nombre}» guardados.")
        return redirect("productos:lista")
    nota = ""
    if producto.lleva_existencias:
        nota = "Para cambiar la existencia use la opción Ajustar en Inventario. Así queda el registro del cambio."
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": f"Editar {producto.nombre}",
        "volver": "productos:lista",
        "nota": nota,
        "script": "js/productos.js",
    })


@solo_administrador
@require_POST
def cambiar_estado_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    servicios.cambiar_estado_producto(producto, request.user)
    if producto.activo:
        messages.success(request, f"«{producto.nombre}» está activo otra vez.")
    else:
        messages.success(request, f"«{producto.nombre}» quedó inactivo. Su historial se conserva.")
    return redirect("productos:lista")


@solo_administrador
def lista_categorias(request):
    categorias = Categoria.objects.annotate(total_productos=Count("producto"))
    return render(request, "productos/categorias.html", {"categorias": categorias})


@solo_administrador
def crear_categoria(request):
    formulario = CategoriaForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        categoria = formulario.save()
        messages.success(request, f"Categoría «{categoria.nombre}» guardada.")
        return redirect("productos:categorias")
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": "Nueva categoría",
        "volver": "productos:categorias",
    })


@solo_administrador
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    formulario = CategoriaForm(request.POST or None, instance=categoria)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, f"Cambios de «{categoria.nombre}» guardados.")
        return redirect("productos:categorias")
    return render(request, "formulario.html", {
        "formulario": formulario,
        "titulo": f"Editar {categoria.nombre}",
        "volver": "productos:categorias",
    })


@solo_administrador
@require_POST
def cambiar_estado_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    servicios.cambiar_estado_categoria(categoria, request.user)
    if categoria.activa:
        messages.success(request, f"Categoría «{categoria.nombre}» activa otra vez.")
    else:
        messages.success(request, f"Categoría «{categoria.nombre}» quedó inactiva. Sus productos no cambian.")
    return redirect("productos:categorias")
