const formulariosConConfirmacion = document.querySelectorAll("form[data-confirmar]");

formulariosConConfirmacion.forEach(function (formulario) {
    formulario.addEventListener("submit", function (evento) {
        if (!confirm(formulario.dataset.confirmar)) {
            evento.preventDefault();
            evento.stopImmediatePropagation();
        }
    });
});

const formulariosUnEnvio = document.querySelectorAll("form[data-un-envio]");

formulariosUnEnvio.forEach(function (formulario) {
    formulario.addEventListener("submit", function () {
        const botones = formulario.querySelectorAll("button[type=submit]");
        botones.forEach(function (boton) {
            boton.disabled = true;
            if (boton.dataset.textoEnviando) {
                boton.textContent = boton.dataset.textoEnviando;
            }
        });
    });
});
