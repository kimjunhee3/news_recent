# app.py
from flask import Flask, render_template

from team_news_back import news_bp
from recent_back import recent_bp

app = Flask(__name__, template_folder="templates")

# 두 기능 블루프린트 등록
app.register_blueprint(news_bp)
app.register_blueprint(recent_bp)

@app.route("/")
def home():
    return render_template("combined.html")

@app.route("/healthz")
def healthz():
    return "ok", 200
