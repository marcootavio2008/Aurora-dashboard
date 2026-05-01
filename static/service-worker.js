self.addEventListener("push", function(event) {
    console.log("Push recebido");

    let data = {};
    try {
        data = event.data.json();
    } catch {
        data = { title: "Aurora", body: "Fallback" };
    }

    self.registration.showNotification(data.title, {
        body: data.body
    });
});
