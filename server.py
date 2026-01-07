from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_sock import Sock
from flask_socketio import SocketIO
import os
import json
import random
import unicodedata
import re
import wikipedia
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

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
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="user")


class House(db.Model):
    __tablename__ = "houses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)


class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    device_type = db.Column(db.String(20), nullable=False)
    config = db.Column(db.JSON, nullable=False)
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"), nullable=False)


with app.app_context():
    db.create_all()

    if User.query.count() == 0:
        admin = User(username="admin", password="admin", role="admin")
        db.session.add(admin)
        db.session.commit()

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

def processar_pesquisa(frase):
    termo = detectar_pesquisa(frase)
    if not termo:
        return None

    resultado = pesquisar_wikipedia(termo)
    return resultado or random.choice(RESPOSTAS_SEM_RESULTADO)

def processar_frase(frase):
    respostas = dicionario.get(frase)
    if not respostas:
        return "Não tenho resposta para isso"
    return random.choice(respostas) if isinstance(respostas, list) else respostas

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
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session.get("username", "Usuário")
    )



@app.route("/dash_residencial")
def dash_residencial():
    house_id = session.get("house_id")
    if not house_id:
        return redirect(url_for("dashboard"))

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
# USUÁRIOS
# ===============================

@app.route("/api/users", methods=["GET"])
def list_users():
    if session.get("role") != "admin":
        return jsonify({"error": "acesso negado"}), 403

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
