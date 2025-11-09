from flask import Flask, render_template, request, jsonify
import subprocess
import psutil
import json
import random
import webbrowser as wb
from bs4 import BeautifulSoup
import urllib.parse
from translate import Translator
import requests
import wikipedia
from datetime import datetime
import datetime as dt
from flask import redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "cx1228"  # Necessário para usar sessão


aurora_proc = None  # Guarda o processo da Aurora
CAMINHO = r"dictionary.json"

with open(CAMINHO, "r", encoding="utf-8") as f:
    dicionario = json.load(f)

def get_dados():
    dia_atual = datetime.now()
    dia_ingles = dia_atual.strftime(f'%A')
    translator = Translator(to_lang='pt', from_lang='en')
    dia = translator.translate(dia_ingles)
    dia_resposta = dia_atual.strftime(f'{dia.capitalize()} %d/%m/%Y')
    API_KEY = "d9d2657ec1b46a818cd8d41288954437"
    cidade = "Barbacena"
    link = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={API_KEY}&lang=pt_br"
    requisicao = requests.get(link)
    requisicao_dic = requisicao.json()
    descricao = requisicao_dic['weather'][0]['description']
    temperatura = requisicao_dic['main']['temp'] - 273.15
    temperatura = int(temperatura)
    clima = f'{descricao.capitalize()}, está fazendo neste momento: {int(temperatura)}°C'
    hora_atual = datetime.now()
    hora_resposta = int(hora_atual.strftime('%H'))
    minutos = hora_atual.strftime('%M')
    hora_resposta = hora_resposta + 3
    horas = f"{hora_resposta}:{minutos}"
    return {
        "Horas: ": horas,
        "Data: ": dia_resposta,
        "Clima: ": clima}

def processar_frase(frase):
    frase = frase.lower()
    if frase in dicionario:
        respostas = dicionario[frase]
        if isinstance(respostas, list):
            return random.choice(respostas)
        return respostas
    else:
        return "Não tenho respostas para isso"

def pesquisar(query):
    wikipedia.set_lang(prefix='pt')
    result = wikipedia.summary(query, sentences=2)
    return result
USERS = {
    "Marco": "2810",
}

# Página inicial -> Login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["usuario"]
        password = request.form["senha"]

        # Validação de usuário
        if username in USERS and USERS[username] == password:
            session["user"] = username  # Guarda o login na sessão
            return redirect(url_for("home"))  # Redireciona para o dashboard
        else:
            return redirect(url_for("login"))

    return render_template("login.html")
# Rota principal (abre o dashboard)
@app.route('/dashboard')
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["user"])

# Rota para a página "Serviços"
@app.route('/casa')
def casa():
    dados = get_dados()
    return render_template('casa.html', dados=dados)

# Inicia a Aurora
@app.route('/start', methods=['POST'])
def start_aurora():
    global aurora_proc
    if aurora_proc is None:
        aurora_proc = subprocess.Popen(
            [r"C:\Users\Marco Otávio\AppData\Local\Programs\Python\Python38\python.exe", r"C:\Users\Marco Otávio\Documents\Marco Otavio\Python\AURORA.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return jsonify({"status": "Aurora iniciada"})
    else:
        return jsonify({"status": "Aurora já estava em execução"})

    # Encerra a Aurora
@app.route('/stop', methods=['POST'])
def stop_aurora():
    global aurora_proc
    if aurora_proc is not None:
        aurora_proc.terminate()
        return jsonify({"status": "Aurora encerrada"})

    pass

@app.route('/message', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get("message").lower()
    # Detecta se é uma pesquisa
    if message.startswith("pesquisar"):
        query = message.replace("pesquisar", "").strip()
        resultados = pesquisar(query)
        return jsonify({"response": resultados})

    if "horas" in message:
        hora_atual = datetime.now()
        hora_resposta = hora_atual.strftime('%H:%M')
        return jsonify({"response": f"São: {hora_resposta}"})

    # Caso contrário, só responde normal
    resposta = processar_frase(message)
    return jsonify({"response": resposta})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
