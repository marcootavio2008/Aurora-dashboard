function salvarConfiguracoes() {
  const dados = {
    nome: document.getElementById('nome').value,
    senha: document.getElementById('senha').value,
  };

  console.log('Configurações:', dados);

  fetch('/api/settings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(dados)
  })
  .then(res => res.json())
  .then(res => {
    alert('Configurações salvas com sucesso!');
  })
  .catch(err => {
    console.error(err);
    alert('Erro ao salvar configurações');
  });
}
