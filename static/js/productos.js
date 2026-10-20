const formaVenta = document.getElementById("id_forma_venta");
const controlInventario = document.getElementById("id_control_inventario");
const campoPrecio = document.getElementById("campo-precio_venta");
const campoMinimo = document.getElementById("campo-existencia_minima");
const campoInicial = document.getElementById("campo-existencia_inicial");

function actualizarCampos() {
    const porImporte = formaVenta.value === "importe";
    const cuentaUnidades = controlInventario.value === "unidades";

    campoPrecio.classList.toggle("campo--oculto", porImporte);
    campoMinimo.classList.toggle("campo--oculto", !cuentaUnidades);
    if (campoInicial) {
        campoInicial.classList.toggle("campo--oculto", !cuentaUnidades);
    }
}

if (formaVenta && controlInventario) {
    formaVenta.addEventListener("change", actualizarCampos);
    controlInventario.addEventListener("change", actualizarCampos);
    actualizarCampos();
}
