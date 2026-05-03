self.addEventListener("push", function(event) {
    console.log("🔔 Push recebido");

    let data = {};
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            // Caso o backend envie texto simples em vez de JSON
            data = { title: "Aurora", body: event.data.text() };
        }
    } else {
        data = { title: "Aurora", body: "Você tem uma nova atualização!" };
    }

    // event.waitUntil garante que o navegador não mate o SW 
    // antes de terminar de exibir a notificação.
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            badge: "/static/file_0000000083f071f590c5479d73121091.png",
            icon: "/static/android-chrome-512x512.png", // certifique-se que este caminho existe
            vibrate: [200, 100, 200],
            data: {
                url: "/" // URL para abrir quando clicar
            }
        })
    );
});

// Lógica para abrir o site ao clicar na notificação
self.addEventListener("notificationclick", function(event) {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then(function(clientList) {
            if (clientList.length > 0) {
                return clientList[0].focus();
            }
            return clients.openWindow("/");
        })
    );
});
