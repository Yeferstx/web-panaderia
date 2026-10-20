const unidades = JSON.parse(document.getElementById("datos-unidades").textContent);
const campoMetodo = document.getElementById("campo-metodo-pago");

function actualizarCompra() {
    let total = 0;
    document.querySelectorAll("#lineas-compra .linea-formulario").forEach(function (linea) {
        if (linea.hidden) {
            return;
        }
        const articulo = linea.querySelector(".campo--articulo select").value;
        const descripcion = linea.querySelector(".campo--descripcion");
        descripcion.classList.toggle("campo--oculto", articulo !== "otro");
        linea.querySelector(".linea-formulario__unidad").textContent = unidades[articulo] || "";
        total += leerPesos(linea.querySelector(".campo--valor input").value);
    });
    document.getElementById("total-compra").textContent = formatoPesos(total);
}

function actualizarPago() {
    const elegida = document.querySelector("input[name=estado_pago]:checked");
    campoMetodo.hidden = elegida && elegida.value === "pendiente";
}

document.querySelectorAll("input[name=estado_pago]").forEach(function (opcion) {
    opcion.addEventListener("change", actualizarPago);
});

prepararLineas("lineas-compra", "plantilla-linea", "agregar-linea", actualizarCompra);
actualizarPago();
