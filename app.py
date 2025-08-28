# app.py
from flask import Flask, render_template, make_response
from flask_cors import CORS

from team_news_back import news_bp
from recent_back import recent_bp

app = Flask(__name__, template_folder="templates")

# ✅ CORS 허용 (프론트/로컬에서 불러와도 프리플라이트 통과)
CORS(app, resources={r"/*": {"origins": "*"}})

# ✅ 파비콘 405/404 방지
@app.route("/favicon.ico")
def favicon():
    return ("", 204)

# ✅ 모든 경로의 OPTIONS 프리플라이트 OK
@app.route("/<path:any_path>", methods=["OPTIONS"])
def cors_preflight(any_path):
    r = make_response("", 204)
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

# 블루프린트 등록
app.register_blueprint(news_bp)
app.register_blueprint(recent_bp)

@app.route("/")
def home():
    return render_template("combined.html")

@app.route("/healthz")
def healthz():
    return "ok", 200
