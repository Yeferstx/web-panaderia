const botonMenu = document.getElementById("boton-menu");
const menuLateral = document.getElementById("menu-lateral");

if (botonMenu && menuLateral) {
    botonMenu.addEventListener("click", function () {
        const abierto = menuLateral.classList.toggle("menu--abierto");
        botonMenu.setAttribute("aria-expanded", abierto);
        botonMenu.textContent = abierto ? "Cerrar" : "Menú";
    });
}
