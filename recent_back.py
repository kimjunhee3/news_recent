# recent_back.py
from flask import Blueprint, render_template, jsonify
from recent import fetch_recent_results
from flask_cors import CORS

recent_bp = Blueprint("recent", __name__, template_folder="templates")
CORS(recent_bp)

teams = ["한화", "LG", "롯데", "KIA", "SSG", "KT", "삼성", "NC", "두산", "키움"]

@recent_bp.route("/api/recent/<team>")
def api_recent(team):
    try:
        match_results = fetch_recent_results(team)
    except Exception:
        match_results = ["-"] * 5
    return jsonify({"results": (match_results + ["-"] * 5)[:5]})

@recent_bp.route("/recent")
def recent_index():
    results = []
    for team in teams:
        try:
            match_results = fetch_recent_results(team)
        except Exception:
            match_results = ["-"] * 5
        results.append({
            "team": team,
            "results": (match_results + ["-"] * 5)[:5]
        })
    return render_template("recent.html", results=results)
