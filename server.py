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
import os
from flask_sqlalchemy import SQLAlchemy
import unicodedata
import re

app = Flask(__name__)
app.secret_key = "cx1228"

@app.before_request
def check_login():
    allowed_routes = ["login", "static"]

    if request.endpoint not in allowed_routes and "user" not in session: 
        return redirect(url_for("login"))

database_url = os.environ.get("DATABASE_URL")

# ajuste necessário no Render
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
  # Necessário para usar sessão
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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="user")
with app.app_context():
    db.create_all()

    if User.query.count() == 0:
        admin = User(
            username="admin",
            password="admin",
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()


# ==============================
# CONFIGURAÇÕES
# ==============================

wikipedia.set_lang("pt")

GATILHOS_PESQUISA = [
    "pesquisar",
    "buscar",
    "procurar",
    "quem e",
    "quem foi",
    "o que e",
    "o que significa",
    "me fale sobre",
    "explique",
    "defina",
    "pesquise",
    "como aconteceu",
    "como e",
    "qual o"
]


RESPOSTAS_SEM_RESULTADO = [
    "Não encontrei informações confiáveis sobre isso",
    "Esse assunto não parece estar bem documentado",
    "Ainda não achei nada relevante sobre esse tema"
]

# ==============================
# NORMALIZAÇÃO DE TEXTO
# ==============================

def normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto

# ==============================
# DETECÇÃO DE PESQUISA
# ==============================

def detectar_pesquisa(frase: str):
    for gatilho in GATILHOS_PESQUISA:
        if frase.startswith(gatilho):
            termo = frase.replace(gatilho, "").strip()
            if termo:
                return termo
    return None

# ==============================
# PESQUISA NA WIKIPEDIA
# ==============================

def pesquisar_wikipedia(termo: str):
    try:
        return wikipedia.summary(termo, sentences=2)

    except wikipedia.exceptions.DisambiguationError as e:
        sugestoes = ", ".join(e.options[:3])
        return f"Esse termo é ambíguo. Você quis dizer: {sugestoes}?"

    except wikipedia.exceptions.PageError:
        return None

    except Exception:
        return None

# ==============================
# FALLBACK
# ==============================

def resposta_sem_resultado():
    return random.choice(RESPOSTAS_SEM_RESULTADO)

# ==============================
# FUNÇÃO FINAL (USE ESSA)
# ==============================

def processar_pesquisa(frase_original: str):
    frase = normalizar(frase_original)

    termo = detectar_pesquisa(frase)
    if not termo:
        return None  # não é pesquisa

    resultado = pesquisar_wikipedia(termo)

    if resultado:
        return(resultado)

    return resposta_sem_resultado()


with open(CAMINHO, "r", encoding="utf-8") as f:
    dicionario = json.load(f)

def get_dados():
    #data
    agora_br = datetime.now(ZoneInfo("America/Sao_Paulo"))
    day_en = agora_br.strftime(f'%A')
    dia = (dias[day_en])
    dia_resposta = agora_br.strftime(f'{dia}, %d/%m/%Y')
    #horas
    hora_resposta = agora_br.strftime('%H:%M')
    horas = f"{hora_resposta}"
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


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("usuario")
        password = request.form.get("senha")
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session["user"] = user.username
            session["role"] = user.role
            session["user_id"] = user.id

        return redirect(url_for("home"))
    
    return render_template("login.html")


# Rota principal (abre o dashboard)
@app.route('/dashboard')
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["user"])


@app.route("/dash_residencial")
def dash_residencial():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return redirect(
        f"https://controle-dispositivos.onrender.com/"
        f"?user_id={session['user_id']}&role={session['role']}"
    )


# Rota para a página "Serviços"
@app.route('/casa')
def casa():
    dados = get_dados()
    return render_template('casa.html', dados=dados)

@app.route('/controles')
def controles():
    return render_template('controles.html')  # renderiza a página de controle

@app.route('/configs')
def configs():
    return render_template('config.html')

@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.get_json()

    username = data.get("usuario")
    password = data.get("senha")
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "dados inválidos"}), 400

    novo = User(username=username, password=password, role=role)
    db.session.add(novo)
    db.session.commit()

    return jsonify({"status": "usuário criado"})
    return redirect(url_for("login"))

@app.route("/api/users", methods=["GET"])
def list_users():
    if "user" not in session or session.get("role") != "admin":
        return jsonify({"error": "acesso negado"}), 403

    users = User.query.all()
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "role": u.role
        } for u in users
    ])

@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    # 🔒 só admin pode apagar usuário
    if session.get("role") != "admin":
        return jsonify({"error": "acesso negado"}), 403

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "usuário não encontrado"}), 404

    # 🚫 REGRA IMPORTANTE (AQUI ENTRA O SEU IF)
    if user.role == "admin":
        return jsonify({"error": "admin não pode ser removido"}), 403

    db.session.delete(user)
    db.session.commit()

    return jsonify({"status": "usuário removido"})

@app.route('/message', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get("message", "")
    message = normalizar(message)

    # 🔍 TENTA PROCESSAR COMO PESQUISA
    resposta_pesquisa = processar_pesquisa(message)
    if resposta_pesquisa:
        return jsonify({"response": resposta_pesquisa})

    # 💬 CONVERSA NORMAL
    resposta = processar_frase(message)
    return jsonify({"response": resposta})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
