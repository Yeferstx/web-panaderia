const botonVerClave = document.getElementById("ver-clave");
const campoClave = document.getElementById("id_password");

botonVerClave.addEventListener("click", function () {
    const oculta = campoClave.type === "password";
    campoClave.type = oculta ? "text" : "password";
    botonVerClave.textContent = oculta ? "Ocultar" : "Mostrar";
    campoClave.focus();
});
