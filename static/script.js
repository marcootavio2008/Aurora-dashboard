// ===============================
// MENU LATERAL
// ===============================
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


// ===============================
// AURORA FALA
// ===============================
function auroraFalar(texto) {
    if ('speechSynthesis' in window) {
        const fala = new SpeechSynthesisUtterance(texto);
        fala.lang = 'pt-BR';
        fala.pitch = 1;
        fala.rate = 1;
        fala.volume = 1;
        speechSynthesis.speak(fala);
    }
}


// ===============================
// CONTROLE DE LUZ
// ===============================
function toggleLuz(el) {
    const estado = el.checked ? "ligar" : "desligar";

    fetch(`/controle_luz?acao=${estado}`)
        .then(res => res.json())
        .then(data => console.log(data))
        .catch(err => console.error(err));
}


// ===============================
// CHAT
// ===============================
async function sendMessage() {
    const msg = document.getElementById('inputMsg').value;
    if (!msg) return;

    const res = await fetch('/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
    });

    const data = await res.json();

    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML += `<p><b>Você:</b> ${msg}</p>`;
    messagesDiv.innerHTML += `<p><b>Aurora:</b> ${data.response}</p>`;

    auroraFalar(data.response);

    document.getElementById('inputMsg').value = "";
}


// ===============================
// PUSH NOTIFICATION
// ===============================

let swRegistration = null;


// Converter VAPID KEY
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = atob(base64);
    return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
}


// ===============================
// REGISTRO DO SERVICE WORKER
// ===============================
document.addEventListener("DOMContentLoaded", async () => {
    if (!("serviceWorker" in navigator)) {
        console.log("Service Worker não suportado");
        return;
    }

    try {
        swRegistration = await navigator.serviceWorker.register("/service-worker.js");
        console.log("✅ Service Worker registrado");
    } catch (err) {
        console.error("❌ Erro ao registrar SW:", err);
    }
});


// ===============================
// ATIVAR NOTIFICAÇÕES (CHAMAR NO BOTÃO)
// ===============================
async function enableNotifications() {
    if (!swRegistration) {
        console.log("SW ainda não carregado");
        return;
    }

    const permission = await Notification.requestPermission();

    if (permission !== "granted") {
        console.log("❌ Permissão negada");
        return;
    }

    await subscribeUser(swRegistration);
}


// ===============================
// INSCRIÇÃO PUSH
// ===============================
async function subscribeUser(registration) {
    try {
        let subscription = await registration.pushManager.getSubscription();

        if (!subscription) {
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(
                    "BFmyZPH_eZg-3Uj3VvmXEJXO5IFKQRadp5pWKs1Rx5jE0QPO0FjodSgBwj6L_B0NraDhu8jykMJ6F8V7LONPe4o"
                )
            });

            console.log("🆕 Nova inscrição criada");
        } else {
            console.log("ℹ️ Já inscrito");
        }

        const res = await fetch("/save-subscription", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(subscription)
        });

        const data = await res.json();
        console.log("📡 Backend:", data);

    } catch (err) {
        console.error("❌ Erro no subscribe:", err);
    }
}
