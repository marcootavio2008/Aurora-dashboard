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
from pywebpush import webpush, WebPushException

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
    rotas_livres = {
        "login",
        "static",
        "notify",             # 🔥 ADICIONE
        "save_sub"            # 🔥 ADICIONE (nome da função)
    }

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

class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    data = db.Column(db.JSON, nullable=False)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="user")
    
    # Foreign key para a casa do usuário
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"), nullable=True)
    
    # Relacionamento explícito
    house = db.relationship("House", foreign_keys=[house_id], backref="users")

class House(db.Model):
    __tablename__ = "houses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    
    # Dono da casa (um usuário)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    # Relacionamento explícito
    owner = db.relationship("User", foreign_keys=[owner_id], backref="owned_houses")

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    config = db.Column(db.JSON, default={})
    
    # Conserta a referência correta da tabela
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


# ===============================
# CRIAR ADMIN PADRÃO COM CASA
# ===============================

with app.app_context():
    db.create_all()

    if User.query.count() == 0:
        # Cria o admin primeiro
        admin = User(username="admin", password="admin", role="admin")
        db.session.add(admin)
        db.session.commit()  # precisa do id do admin

        # Cria a casa padrão do admin
        admin_house = House(name="Casa Admin", owner_id=admin.id)
        db.session.add(admin_house)
        db.session.commit()  # precisa do id da casa

        # Atualiza o admin com house_id
        admin.house_id = admin_house.id
        db.session.commit()

        print(">>> Admin padrão criado: admin / admin com casa associada")

# ===============================
# CHATBOT / AURORA
# ===============================

MEMORIA_USUARIOS = {}

PALAVRAS_CONTINUACAO = [
    "e", "ai", "entao", "mas",
    "fala mais", "continua",
    "sei la", "hm", "hmm",
    "ata", "ahn"
]

wikipedia.set_lang("pt")
subscriptions = []
VAPID_PUBLIC = "BFmyZPH_eZg-3Uj3VvmXEJXO5IFKQRadp5pWKs1Rx5jE0QPO0FjodSgBwj6L_B0NraDhu8jykMJ6F8V7LONPe4o"
VAPID_PRIVATE = "bP5irRD_aRrWXx-_2KSAbJUENTyQa7CLi6p_-xSxhF4"
CAMINHO = "dictionary.json"

with open(CAMINHO, "r", encoding="utf-8") as f:
    dicionario = json.load(f)

GATILHOS_PESQUISA = [
    "pesquisar", "buscar", "procurar", "quem e",
    "quem foi", "o que e", "o que significa",
    "me fale sobre", "explique", "defina", "quando foi", "qual é"
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

def eh_continuacao(texto):
    palavras = texto.split()
    if len(palavras) <= 2:
        return True
    for p in PALAVRAS_CONTINUACAO:
        if texto.startswith(p):
            return True
    return False

def processar_frase(frase, user_id):
    global MEMORIA_USUARIOS

    if user_id not in MEMORIA_USUARIOS:
        MEMORIA_USUARIOS[user_id] = {
            "ultima_chave": None,
            "historico": [],
            "reutilizacoes": 0
        }

    memoria = MEMORIA_USUARIOS[user_id]

    # 1️⃣ Resposta direta
    if frase in dicionario:
        respostas = dicionario[frase]

        if isinstance(respostas, list):
            ultima_resposta = None
            if memoria["historico"]:
                ultima_resposta = memoria["historico"][-1]["bot"]

            opcoes = [r for r in respostas if r != ultima_resposta]
            resposta = random.choice(opcoes if opcoes else respostas)
        else:
            resposta = respostas

        memoria["ultima_chave"] = frase
        memoria["reutilizacoes"] = 0

    # 2️⃣ Continuação
    elif eh_continuacao(frase) and memoria["ultima_chave"] in dicionario:
        respostas = dicionario[memoria["ultima_chave"]]

        if isinstance(respostas, list):
            resposta = random.choice(respostas)
        else:
            resposta = respostas

        memoria["reutilizacoes"] += 1

        if memoria["reutilizacoes"] > 2:
            resposta = "Sobre o que você quer falar agora?"
            memoria["ultima_chave"] = None
            memoria["reutilizacoes"] = 0

    else:
        resposta = "Não entendi muito bem."

    # atualizar histórico
    memoria["historico"].append({
        "user": frase,
        "bot": resposta
    })

    if len(memoria["historico"]) > 10:
        memoria["historico"].pop(0)

    MEMORIA_USUARIOS[user_id] = memoria

    return resposta
# ===============================
# ROTAS AUTH
# ===============================

@app.route("/service-worker.js")
def sw():
    return app.send_static_file("service-worker.js")

@app.route("/save-subscription", methods=["POST"])
def save_sub():
    if "user_id" not in session:
        return {"error": "não autenticado"}, 403
    sub = request.json
    nova = PushSubscription(
        user_id=session["user_id"],
        data=sub
    )
    db.session.add(nova)
    db.session.commit()
    return {"status": "ok"}

@app.route("/notify", methods=["POST"])
def notify():
    data = request.json
    user_id = data.get("user_id")  # 🔥 importante
    subs = PushSubscription.query.filter_by(user_id=user_id).all()
    for s in subs:
        try:
            webpush(
                subscription_info=s.data,
                data=json.dumps(data),
                vapid_private_key=VAPID_PRIVATE,
                vapid_claims={"sub": "mailto:marcootavio2008@gmail.com"}
            )
        except Exception as e:
            print("Erro:", e)
    return {"status": "ok"}

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
            session["house_id"] = user.house_id  # <- aqui
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
    houses = House.query.all()
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
    house_id = data.get("house_id")  # novo

    if not username or not password:
        return jsonify({"error": "usuário e senha obrigatórios"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "usuário já existe"}), 400

    novo_user = User(username=username, password=password, role=role, house_id=house_id)
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
    user_id = session.get("user_id")

    # Pesquisa primeiro
    resposta_pesquisa = processar_pesquisa(frase)
    if resposta_pesquisa:
        return jsonify({"response": resposta_pesquisa})

    # Conversa contextual
    resposta = processar_frase(frase, user_id)

    return jsonify({"response": resposta})

# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
