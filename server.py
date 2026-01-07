from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import subprocess 
import psutil 
import json 
import random 
from bs4 import BeautifulSoup 
import urllib.parse 
from translate import Translator 
import requests 
import wikipedia 
from datetime import datetime 
from zoneinfo import ZoneInfo 
import datetime as dt 
from flask_socketio import SocketIO 
from datetime import timedelta 
from flask_sock import Sock 
import os 
from flask_sqlalchemy import SQLAlchemy 
import unicodedata 
import re

# ===============================
# APP
# ===============================

app = Flask(__name__)
app.secret_key = "cx1228"

socketio = SocketIO(app)
sock = Sock(app)

# ===============================
# LOGIN GUARD
# ===============================

@app.before_request
def check_login():
    rotas_livres = {"login", "static"}

    if request.endpoint not in rotas_livres and "user_id" not in session:
        return redirect(url_for("login"))

# ===============================
# DATABASE
# ===============================

database_url = os.environ.get("DATABASE_URL")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ===============================
# MODELOS
# ===============================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="user")
    
class House(db.Model):
    __tablename__ = "houses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    config = db.Column(db.JSON, default={})
    house_id = db.Column(db.Integer, db.ForeignKey("house.id"), nullable=False)
    
    # ADICIONE esta linha:
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

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
        print(">>> Admin padrão criado: admin / admin")

# ===============================
# CHATBOT / AURORA
# ===============================

wikipedia.set_lang("pt")

CAMINHO = "dictionary.json"

with open(CAMINHO, "r", encoding="utf-8") as f:
    dicionario = json.load(f)

GATILHOS_PESQUISA = [
    "pesquisar", "buscar", "procurar", "quem e",
    "quem foi", "o que e", "o que significa",
    "me fale sobre", "explique", "defina"
]

RESPOSTAS_SEM_RESULTADO = [
    "Não encontrei informações confiáveis",
    "Esse assunto não está bem documentado",
    "Ainda não achei nada relevante"
]

def normalizar(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    texto = re.sub(r"[^\w\s]", "", texto)
    return re.sub(r"\s+", " ", texto)

def detectar_pesquisa(frase):
    for g in GATILHOS_PESQUISA:
        if frase.startswith(g):
            termo = frase.replace(g, "").strip()
            return termo if termo else None
    return None

def pesquisar_wikipedia(termo):
    try:
        return wikipedia.summary(termo, sentences=2)
    except:
        return None

dias = { 
    "Monday": "Segunda-feira", 
    "Tuesday": "Terça-feira", 
    "Wednesday": "Quarta-feira", 
    "Thursday": "Quinta-feira", 
    "Friday": "Sexta-feira", 
    "Saturday": "Sábado", 
    "Sunday": "Domingo", }

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
    return {"Horas: ": horas, 
            "Data: ": dia_resposta, 
            "Clima: ": clima, 
            "Umidade: ": umidade}

def processar_pesquisa(frase):
    termo = detectar_pesquisa(frase)
    if not termo:
        return None

    resultado = pesquisar_wikipedia(termo)
    return resultado or random.choice(RESPOSTAS_SEM_RESULTADO)

def processar_frase(frase): 
    frase = frase.lower() 
    if frase in dicionario: 
        respostas = dicionario[frase] 
        if isinstance(respostas, list): 
            return random.choice(respostas) 
        return respostas 
    else: return "Não tenho respostas para isso"
# ===============================
# ROTAS AUTH
# ===============================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            username=request.form["usuario"],
            password=request.form["senha"]
        ).first()

        if user:
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/dashboard")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session.get("username", "Usuário")
    )

@app.route('/casa') 
def casa(): 
    dados = get_dados() 
    return render_template('casa.html', dados=dados)

@app.route("/configs")
def configs():
    return render_template("config.html")
    
@app.route("/dash_residencial")
def dash_residencial():
    house_id = session.get("house_id")
    if not house_id:
        return redirect(url_for("home"))

    return redirect(
        f"https://controle-dispositivos.onrender.com/"
        f"?user_id={session['user_id']}&house_id={house_id}"
    )

# ===============================
# CASAS
# ===============================

@app.route("/api/houses", methods=["GET"])
def list_houses():
    houses = House.query.filter_by(owner_id=session["user_id"]).all()
    return jsonify([{"id": h.id, "name": h.name} for h in houses])


@app.route("/api/houses", methods=["POST"])
def create_house():
    name = request.json.get("name")

    if not name:
        return jsonify({"error": "nome inválido"}), 400

    house = House(name=name, owner_id=session["user_id"])
    db.session.add(house)
    db.session.commit()

    return jsonify({"status": "ok", "house_id": house.id})


@app.route("/api/houses/select", methods=["POST"])
def select_house():
    house_id = request.json.get("house_id")

    house = House.query.filter_by(
        id=house_id,
        owner_id=session["user_id"]
    ).first()

    if not house:
        return jsonify({"error": "casa inválida"}), 403

    session["house_id"] = house.id
    return jsonify({"status": "ok"})


# ===============================
# CONFIGURAÇÕES DO USUÁRIO
# ===============================

@app.route("/api/users", methods=["POST"])
def add_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "usuário e senha obrigatórios"}), 400

    # Checar se o usuário já existe
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "usuário já existe"}), 400

    novo_user = User(username=username, password=password, role=role)
    db.session.add(novo_user)
    db.session.commit()

    return jsonify({"status": "ok", "user_id": novo_user.id})

@app.route("/api/users", methods=["GET"])
def list_users():
    users = User.query.all()
    return jsonify([
        {"id": u.id, "username": u.username, "role": u.role}
        for u in users
    ])


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    if session.get("role") != "admin":
        return jsonify({"error": "acesso negado"}), 403

    user = User.query.get(user_id)

    if not user or user.role == "admin":
        return jsonify({"error": "operação inválida"}), 403

    db.session.delete(user)
    db.session.commit()

    return jsonify({"status": "removido"})

# ===============================
# CHAT
# ===============================

@app.route("/message", methods=["POST"])
def send_message():
    frase = normalizar(request.json.get("message", ""))

    resposta = processar_pesquisa(frase)
    if resposta:
        return jsonify({"response": resposta})

    return jsonify({"response": processar_frase(frase)})

# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
