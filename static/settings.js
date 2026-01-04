function salvarConfiguracoes() {
  const usuario = document.getElementById('nome').value;
  const senha = document.getElementById('senha').value;
  const role = document.getElementById('role').value; // select ou input

  fetch("/api/settings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      usuario: usuario,
      senha: senha,
      role: role
    })
  })
  .then(res => res.json())
  .then(data => {
    console.log("Resposta:", data);
    alert("Usuário salvo com sucesso!");
  })
  .catch(err => {
    console.error("Erro:", err);
    alert("Erro ao salvar usuário");
  });
}
