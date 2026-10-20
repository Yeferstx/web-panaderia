function prepararLineas(idContenedor, idPlantilla, idBotonAgregar, alCambiar) {
    const contenedor = document.getElementById(idContenedor);
    const plantilla = document.getElementById(idPlantilla);
    const prefijo = contenedor.dataset.prefijo;
    const totalFormularios = document.getElementById("id_" + prefijo + "-TOTAL_FORMS");

    function activarLinea(linea) {
        linea.querySelector(".linea-formulario__quitar").addEventListener("click", function () {
            linea.querySelectorAll("input, select, textarea").forEach(function (campo) {
                campo.value = "";
            });
            const visibles = contenedor.querySelectorAll(".linea-formulario:not([hidden])").length;
            if (visibles > 1) {
                linea.hidden = true;
            }
            alCambiar();
        });
        linea.querySelectorAll("input, select").forEach(function (campo) {
            campo.addEventListener("input", alCambiar);
            campo.addEventListener("change", alCambiar);
        });
    }

    document.getElementById(idBotonAgregar).addEventListener("click", function () {
        const numero = Number(totalFormularios.value);
        const html = plantilla.innerHTML.replace(/__prefix__/g, numero);
        contenedor.insertAdjacentHTML("beforeend", html);
        totalFormularios.value = numero + 1;
        const nueva = contenedor.lastElementChild;
        activarLinea(nueva);
        nueva.querySelector("select, input").focus();
        alCambiar();
    });

    contenedor.querySelectorAll(".linea-formulario").forEach(activarLinea);
    alCambiar();
}

function leerPesos(texto) {
    return Number(String(texto).replace(/\$/g, "").replace(/\./g, "").replace(/,/g, "").replace(/\s/g, "")) || 0;
}

function formatoPesos(valor) {
    return "$" + Math.round(valor).toLocaleString("es-CO");
}
