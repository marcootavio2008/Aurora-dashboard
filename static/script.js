document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.querySelector('.menu-toggle');
    const closeBtn = document.querySelector('.close-btn');
    const sidebarMenu = document.querySelector('.sidebar-menu');

    if (menuToggle && closeBtn && sidebarMenu) {
        menuToggle.addEventListener('click', () => {
            sidebarMenu.classList.add('open');
        });

        closeBtn.addEventListener('click', () => {
            sidebarMenu.classList.remove('open');
        });

        document.addEventListener('click', (event) => {
            if (!sidebarMenu.contains(event.target) && !menuToggle.contains(event.target)) {
                sidebarMenu.classList.remove('open');
            }
        });
    }
});


function auroraFalar(texto) {
    if ('speechSynthesis' in window) {
        const fala = new SpeechSynthesisUtterance(texto);
        fala.lang = 'pt-BR';  // Português do Brasil
        fala.pitch = 1;       // Tom de voz (0 a 2)
        fala.rate = 1;        // Velocidade da fala
        fala.volume = 1;      // Volume (0 a 1)

        speechSynthesis.speak(fala);
    } else {
        console.log("A API de fala não é suportada neste navegador.");
    }
}


function toggleLuz(el) {
    const estado = el.checked ? "ligar" : "desligar";

    fetch(`/controle_luz?acao=${estado}`)
        .then(res => res.json())
        .then(data => console.log(data))
        .catch(err => console.error(err));
}


async function sendMessage() {
    let msg = document.getElementById('inputMsg').value;
    if (!msg) return;

    let res = await fetch('/message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: msg})
    });
    let data = await res.json();

    let messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML += `<p><b>Você:</b> ${msg}</p>`;
    messagesDiv.innerHTML += `<p><b>Aurora:</b> ${data.response}</p>`;
    auroraFalar(data.response);

    document.getElementById('inputMsg').value = "";
}
