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
from pyfirmata import *
from datetime import datetime
from zoneinfo import ZoneInfo
import datetime as dt
from flask_socketio import SocketIO
from flask import redirect, url_for, session, flash
from datetime import timedelta
from flask_sock import Sock

app = Flask(__name__)
app.secret_key = "cx1228"  # Necessário para usar sessão
socketio = SocketIO(app)
sock = Sock(app)
connections = []
dias = {
    "Monday": "Segunda-feira",
    "Tuesday": "Terça-feira",
    "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira",
    "Friday": "Sexta-feira",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}
aurora_proc = None  # Guarda o processo da Aurora
CAMINHO = r"dictionary.json"

with open(CAMINHO, "r", encoding="utf-8") as f:
    dicionario = json.load(f)

def get_dados():
    #data
    agora_br = datetime.now(ZoneInfo("America/Sao_Paulo"))
    dia = agora_br.strftime(f'%A')
    dia = (dias[day_en])
    translator = Translator(to_lang='pt', from_lang='en')
    dia = translator.translate(dia_ingles)
    dia_resposta = agora_br.strftime(f'{dia}, %d/%m/%Y')
    #clima
    API_KEY = "d9d2657ec1b46a818cd8d41288954437"
    cidade = "Barbacena"
    link = f"https://api.openweathermap.org/data/2.5/weather?q={cidade}&appid={API_KEY}&lang=pt_br"
    requisicao = requests.get(link)
    requisicao_dic = requisicao.json()
    descricao = requisicao_dic['weather'][0]['description']
    temperatura = requisicao_dic['main']['temp'] - 273.15
    temperatura = int(temperatura)
    umidade = requisicao_dic['main']['humidity']
    umidade = f"Umidade: {umidade}%"
    clima = f'{descricao.capitalize()}, está fazendo neste momento: {int(temperatura)}°C'
    #horas
    hora_resposta = agora_br.strftime('%H:%M')
    horas = f"{hora_resposta}"


    return {
        "Horas: ": horas,
        "Data: ": dia_resposta,
        "Clima: ": clima,
        "Umidade: ": umidade}

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

@sock.route('/ws')
def ws_endpoint(ws):
    connections.append(ws)
    print("PC conectado via WebSocket")

    try:
        while True:
            msg = ws.receive(timeout=1)   # <<< NÃO BLOQUEIA
            if msg:
                print("Mensagem recebida:", msg)
    except:
        print("PC desconectado")
    finally:
        if ws in connections:
            connections.remove(ws)


@app.route("/controle_luz")
def controle_luz():
    acao = request.args.get("acao")

    if acao == "ligar":
        print("Enviando comando LIGAR")
        for pc in connections:
            try:
                pc.send("LIGAR_LUZ")
            except:
                pass

        return jsonify({"status": "luz ligada"})

    elif acao == "desligar":
        print("Enviando comando DESLIGAR")
        for pc in connections:
            try:
                pc.send("DESLIGAR_LUZ")
            except:
                pass

        return jsonify({"status": "luz desligada"})

    return jsonify({"erro": "comando invalido"})


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

@app.route('/localizacao')
def localizacao():
    ip = request.remote_addr
    r = requests.get(f"http://ip-api.com/json/{ip}").json()
    return {
        "cidade": r["city"],
        "pais": r["country"],
        "latitude": r["lat"],
        "longitude": r["lon"]
    }

# Rota para a página "Serviços"
@app.route('/casa')
def casa():
    dados = get_dados()
    return render_template('casa.html', dados=dados)

@app.route('/controles')
def controles():
    return render_template('controles.html')  # renderiza a página de controle


@app.route('/message', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get("message").lower()
    # Detecta se é uma pesquisa
    if message.startswith("pesquisar"):
        query = message.replace("pesquisar", "").strip()
        resultados = pesquisar(query)
        return jsonify({"response": resultados})

    # Caso contrário, só responde normal
    resposta = processar_frase(message)
    return jsonify({"response": resposta})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
