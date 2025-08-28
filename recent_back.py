# recent_back.py
from flask import Blueprint, render_template, jsonify, request, make_response
from flask_cors import CORS
from recent import fetch_recent_results

# 팀 이름 정규화: team_news.py의 normalize_team_display를 우선 사용
try:
    from team_news import normalize_team_display  # 표준표기(한화/두산/…)로 변환
except Exception:
    normalize_team_display = None

recent_bp = Blueprint("recent", __name__, template_folder="templates")
CORS(recent_bp, resources={r"/*": {"origins": "*"}})

# 기본 팀 목록(표시 순서)
TEAMS = ["한화", "LG", "롯데", "KIA", "SSG", "KT", "삼성", "NC", "두산", "키움"]

# normalize_team_display 미사용 시 대비용(간단 별칭 매핑)
_FALLBACK_ALIAS = {
    # KT
    "kt": "KT", "wiz": "KT", "ktwiz": "KT", "케이티": "KT",
    # LG
    "lg": "LG", "엘지": "LG",
    # KIA
    "kia": "KIA", "기아": "KIA", "tigers": "KIA", "해태": "KIA", "해태타이거즈": "KIA",
    # 두산
    "doosan": "두산", "두산": "두산", "ob": "두산", "obbears": "두산", "bears": "두산",
    # 한화
    "hanwha": "한화", "한화": "한화", "eagles": "한화",
    # SSG
    "ssg": "SSG", "sk": "SSG", "wyverns": "SSG", "와이번스": "SSG", "랜더스": "SSG",
    # 키움
    "kiwoom": "키움", "키움": "키움", "히어로즈": "키움", "heroes": "키움", "넥센": "키움",
    # 삼성
    "samsung": "삼성", "삼성": "삼성", "lions": "삼성",
    # NC
    "nc": "NC", "엔씨": "NC", "dinos": "NC",
    # 롯데
    "lotte": "롯데", "롯데": "롯데", "giants": "롯데",
}

def _normalize_team(name: str | None) -> str | None:
    """영문/별칭/한글 어떤 입력이 와도 템플릿에서 쓰는 표준표기(한화/두산/…)로 변환."""
    if not name:
        return None
    s = str(name).strip()
    if normalize_team_display:
        return normalize_team_display(s)
    # fallback
    k = s.replace(" ", "").lower()
    return _FALLBACK_ALIAS.get(k, s)

# ----------- CORS 프리플라이트(405 방지) -----------
@recent_bp.route("/recent", methods=["OPTIONS"])
@recent_bp.route("/api/recent/<team>", methods=["OPTIONS"])
def recent_options(team=None):
    r = make_response("", 204)
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

# ----------- API: 단일 팀 결과 JSON -----------
@recent_bp.route("/api/recent/<team>", methods=["GET"])
def api_recent(team):
    team_norm = _normalize_team(team) or team
    try:
        match_results = fetch_recent_results(team_norm)
    except Exception:
        match_results = ["-"] * 5
    return jsonify({"team": team_norm, "results": (match_results + ["-"] * 5)[:5]})

# ----------- 페이지: ?team= 이면 단일 팀, 없으면 전체 -----------
@recent_bp.route("/recent", methods=["GET"])
def recent_index():
    team_q = request.args.get("team")  # 예: hanwha, 한화, eagles …
    results = []

    if team_q:
        team_norm = _normalize_team(team_q) or team_q
        try:
            match_results = fetch_recent_results(team_norm)
        except Exception:
            match_results = ["-"] * 5
        results.append({
            "team": team_norm,
            "results": (match_results + ["-"] * 5)[:5],
        })
    else:
        for t in TEAMS:
            try:
                match_results = fetch_recent_results(t)
            except Exception:
                match_results = ["-"] * 5
            results.append({
                "team": t,
                "results": (match_results + ["-"] * 5)[:5],
            })

    return render_template("recent.html", results=results)
