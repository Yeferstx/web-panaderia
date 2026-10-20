const productos = JSON.parse(document.getElementById("datos-productos").textContent);
const productosPorId = {};
productos.forEach(function (producto) {
    productosPorId[producto.id] = producto;
});

let lineas = [];
let categoriaElegida = "";
let productoImporte = null;

const contenedorProductos = document.getElementById("productos-venta");
const buscador = document.getElementById("buscar-producto");
const sinResultados = document.getElementById("sin-resultados");
const listaLineas = document.getElementById("lineas");
const lineasVacio = document.getElementById("lineas-vacio");
const textoTotal = document.getElementById("total");
const campoLineas = document.getElementById("campo-lineas");
const botonGuardar = document.getElementById("boton-guardar");
const botonVaciar = document.getElementById("boton-vaciar");
const barraTotal = document.getElementById("barra-total");
const barraTotalTexto = document.getElementById("barra-total-texto");

const panelImporte = document.getElementById("panel-importe");
const importeNombre = document.getElementById("importe-nombre");
const importeValor = document.getElementById("importe-valor");
const importeError = document.getElementById("importe-error");

function formatoPesos(valor) {
    return "$" + Math.round(valor).toLocaleString("es-CO");
}

function formatoCantidad(valor) {
    return Number(valor).toLocaleString("es-CO", { maximumFractionDigits: 3 });
}

function leerNumero(texto) {
    const limpio = String(texto).replace(/\$/g, "").replace(/\./g, "").replace(/\s/g, "");
    return Number(limpio);
}

function mostrarProductos() {
    const texto = buscador.value.trim().toLowerCase();
    contenedorProductos.innerHTML = "";
    let visibles = 0;

    productos.forEach(function (producto) {
        if (categoriaElegida && String(producto.categoria) !== categoriaElegida) {
            return;
        }
        if (texto && !producto.nombre.toLowerCase().includes(texto)) {
            return;
        }
        visibles++;

        const boton = document.createElement("button");
        boton.type = "button";
        boton.className = "producto-venta";
        if (producto.por_importe) {
            boton.classList.add("producto-venta--importe");
        }

        const nombre = document.createElement("span");
        nombre.className = "producto-venta__nombre";
        nombre.textContent = producto.nombre;
        boton.appendChild(nombre);

        const precio = document.createElement("span");
        precio.className = "producto-venta__precio";
        precio.textContent = producto.por_importe ? "Escribir valor" : formatoPesos(producto.precio);
        boton.appendChild(precio);

        if (producto.lleva_existencias) {
            const existencia = document.createElement("span");
            existencia.className = "producto-venta__existencia";
            existencia.textContent = "Quedan " + formatoCantidad(producto.existencia);
            boton.appendChild(existencia);
        }

        boton.addEventListener("click", function () {
            elegirProducto(producto);
        });
        contenedorProductos.appendChild(boton);
    });

    sinResultados.hidden = visibles > 0;
}

function elegirProducto(producto) {
    if (producto.por_importe) {
        abrirPanelImporte(producto);
    } else {
        agregarUnidades(producto, 1);
    }
}

function agregarUnidades(producto, cantidad) {
    const linea = lineas.find(function (item) {
        return item.producto === producto.id;
    });
    if (linea) {
        linea.cantidad += cantidad;
    } else {
        lineas.push({ producto: producto.id, cantidad: cantidad });
    }
    actualizarVenta();
}

function abrirPanelImporte(producto) {
    productoImporte = producto;
    importeNombre.textContent = producto.nombre;
    importeValor.value = "";
    importeError.hidden = true;
    panelImporte.hidden = false;
    importeValor.focus();
}

function cerrarPanelImporte() {
    productoImporte = null;
    panelImporte.hidden = true;
}

function agregarImporte(valor) {
    if (!Number.isInteger(valor) || valor <= 0) {
        importeError.textContent = "Escriba un valor en pesos mayor que cero, sin decimales.";
        importeError.hidden = false;
        importeValor.focus();
        return;
    }

    const linea = lineas.find(function (item) {
        return item.producto === productoImporte.id;
    });
    if (linea) {
        linea.importe += valor;
    } else {
        lineas.push({ producto: productoImporte.id, importe: valor });
    }
    cerrarPanelImporte();
    actualizarVenta();
}

function subtotalDe(linea) {
    if (linea.importe !== undefined) {
        return linea.importe;
    }
    return linea.cantidad * productosPorId[linea.producto].precio;
}

function crearBoton(texto, etiqueta, accion) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "boton boton--secundario boton--pequeno";
    boton.textContent = texto;
    boton.setAttribute("aria-label", etiqueta);
    boton.addEventListener("click", accion);
    return boton;
}

function dibujarLinea(linea, posicion) {
    const producto = productosPorId[linea.producto];
    const item = document.createElement("li");
    item.className = "linea";

    const nombre = document.createElement("div");
    nombre.className = "linea__nombre";
    nombre.textContent = producto.nombre;
    item.appendChild(nombre);

    const detalle = document.createElement("div");
    detalle.className = "linea__detalle";

    if (linea.importe !== undefined) {
        detalle.textContent = "Por valor";
    } else {
        detalle.appendChild(crearBoton("−", "Quitar uno", function () {
            linea.cantidad -= 1;
            if (linea.cantidad <= 0) {
                lineas.splice(posicion, 1);
            }
            actualizarVenta();
        }));

        const cantidad = document.createElement("span");
        cantidad.className = "linea__cantidad";
        cantidad.textContent = formatoCantidad(linea.cantidad) + " × " + formatoPesos(producto.precio);
        detalle.appendChild(cantidad);

        detalle.appendChild(crearBoton("+", "Agregar uno", function () {
            linea.cantidad += 1;
            actualizarVenta();
        }));
    }
    item.appendChild(detalle);

    const subtotal = document.createElement("strong");
    subtotal.className = "linea__subtotal";
    subtotal.textContent = formatoPesos(subtotalDe(linea));
    item.appendChild(subtotal);

    const quitar = crearBoton("Quitar", "Quitar " + producto.nombre, function () {
        lineas.splice(posicion, 1);
        actualizarVenta();
    });
    quitar.classList.add("linea__quitar");
    item.appendChild(quitar);

    if (producto.lleva_existencias && linea.cantidad > producto.existencia) {
        const aviso = document.createElement("p");
        aviso.className = "linea__aviso";
        aviso.textContent = "En el sistema hay " + formatoCantidad(producto.existencia) +
            ". Puede guardar la venta, pero la existencia quedará en negativo y habrá que revisarla.";
        item.appendChild(aviso);
    }

    listaLineas.appendChild(item);
}

function actualizarVenta() {
    listaLineas.innerHTML = "";
    let total = 0;
    let cantidadProductos = 0;

    lineas.forEach(function (linea, posicion) {
        dibujarLinea(linea, posicion);
        total += subtotalDe(linea);
        cantidadProductos += linea.importe !== undefined ? 1 : linea.cantidad;
    });

    const hayLineas = lineas.length > 0;
    lineasVacio.hidden = hayLineas;
    botonVaciar.hidden = !hayLineas;
    botonGuardar.disabled = !hayLineas;
    textoTotal.textContent = formatoPesos(total);
    botonGuardar.textContent = hayLineas ? "Guardar venta de " + formatoPesos(total) : "Guardar venta";
    campoLineas.value = JSON.stringify(lineas);

    barraTotal.hidden = !hayLineas;
    barraTotalTexto.textContent = "Total " + formatoPesos(total) + " (" + formatoCantidad(cantidadProductos) +
        (cantidadProductos === 1 ? " producto)" : " productos)");
}

function recuperarLineas() {
    try {
        const guardadas = JSON.parse(JSON.parse(document.getElementById("datos-lineas").textContent));
        if (!Array.isArray(guardadas)) {
            return;
        }
        guardadas.forEach(function (linea) {
            const producto = productosPorId[linea.producto];
            if (!producto) {
                return;
            }
            if (producto.por_importe && Number(linea.importe) > 0) {
                lineas.push({ producto: producto.id, importe: Number(linea.importe) });
            } else if (!producto.por_importe && Number(linea.cantidad) > 0) {
                lineas.push({ producto: producto.id, cantidad: Number(linea.cantidad) });
            }
        });
    } catch (error) {
        lineas = [];
    }
}

buscador.addEventListener("input", mostrarProductos);

document.querySelectorAll(".categoria").forEach(function (boton) {
    boton.addEventListener("click", function () {
        document.querySelectorAll(".categoria").forEach(function (otro) {
            otro.classList.remove("categoria--activa");
        });
        boton.classList.add("categoria--activa");
        categoriaElegida = boton.dataset.categoria;
        mostrarProductos();
    });
});

document.querySelectorAll("[data-importe]").forEach(function (boton) {
    boton.addEventListener("click", function () {
        agregarImporte(Number(boton.dataset.importe));
    });
});

document.getElementById("importe-agregar").addEventListener("click", function () {
    agregarImporte(leerNumero(importeValor.value));
});

document.getElementById("importe-cancelar").addEventListener("click", cerrarPanelImporte);

importeValor.addEventListener("keydown", function (evento) {
    if (evento.key === "Enter") {
        evento.preventDefault();
        agregarImporte(leerNumero(importeValor.value));
    }
    if (evento.key === "Escape") {
        cerrarPanelImporte();
    }
});

botonVaciar.addEventListener("click", function () {
    if (confirm("¿Quitar todos los productos de esta venta?")) {
        lineas = [];
        actualizarVenta();
    }
});

recuperarLineas();
mostrarProductos();
actualizarVenta();
