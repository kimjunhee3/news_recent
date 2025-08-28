# team_news_back.py
from flask import Blueprint, render_template, request, jsonify, make_response
from flask_cors import CORS
from team_news import (
    fetch_team_news,
    fetch_team_news_fast,
    get_team_code_map,
    count_team_news,
    normalize_team_display,
)
import datetime
import time
import math

PER_PAGE = 4
CACHE_TTL_SEC = 600   # 총 페이지 수 캐시 10분
FAST_TTL_SEC = 120    # 첫 4개 초단기 캐시 2분

news_bp = Blueprint("news", __name__, template_folder="templates")
CORS(news_bp, resources={r"/*": {"origins": "*"}})  # 블루프린트 CORS 허용

# (team_code, date) -> (total_count, cached_at_epoch)
_TOTAL_CACHE: dict[tuple[str, str], tuple[int, float]] = {}
# (team_code, date) -> (first4_items, cached_at_epoch)
_FIRST4_CACHE: dict[tuple[str, str], tuple[list, float]] = {}

def _resolve_team_and_date(args):
    """요청 파라미터의 team을 표준표기로 정규화하고 네이버 팀코드로 변환."""
    raw_name = args.get("team", "롯데")
    team_name = normalize_team_display(raw_name) or "롯데"
    code_map = get_team_code_map()
    team_code = code_map.get(team_name, "LT")
    today = datetime.datetime.now().strftime("%Y%m%d")
    return team_name, team_code, today

# ---- 공용 OPTIONS 응답 (프리플라이트 405 방지) ----
@news_bp.route("/news", methods=["OPTIONS"])
@news_bp.route("/api/news", methods=["OPTIONS"])
@news_bp.route("/api/news_total", methods=["OPTIONS"])
def news_options():
    r = make_response("", 204)
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

# ---- 페이지 진입(첫 4개는 빠르게) ----
@news_bp.route("/news", methods=["GET"])
def index():
    team_name, team_code, today = _resolve_team_and_date(request.args)
    key = (team_code, today)
    now = time.time()

    if key in _FIRST4_CACHE and now - _FIRST4_CACHE[key][1] < FAST_TTL_SEC:
        first4 = _FIRST4_CACHE[key][0]
    else:
        # 1차: requests 기반 초고속
        first4 = fetch_team_news_fast(team_code=team_code, date=today, count=PER_PAGE)
        # 부족하면 selenium으로 보충
        if len(first4) < PER_PAGE:
            first4 = fetch_team_news(team_code=team_code, date=today, needed_count=PER_PAGE)
        _FIRST4_CACHE[key] = (first4, now)

    return render_template(
        "team_news.html",
        team_name=team_name,   # 템플릿/JS가 API 호출할 때 그대로 사용
        news_list=first4,
        current_page=1
    )

# ---- 다음 페이지 묶음 로드(API) ----
@news_bp.route("/api/news", methods=["GET"])
def api_news():
    offset = int(request.args.get("offset", 0))
    buffer_pages = int(request.args.get("buffer", 1))
    buffer_pages = max(1, min(buffer_pages, 5))

    team_name, team_code, today = _resolve_team_and_date(request.args)
    need = offset + PER_PAGE * buffer_pages
    items = fetch_team_news(team_code=team_code, date=today, needed_count=need)

    window_end = offset + PER_PAGE * buffer_pages
    window_items = items[offset:window_end] if offset < len(items) else []
    has_more = len(items) > window_end

    return jsonify({
        "items": window_items,
        "has_more": has_more,
        "per_page": PER_PAGE
    })

# ---- 전체 개수(페이지 수) 조회(API) ----
@news_bp.route("/api/news_total", methods=["GET"])
def api_news_total():
    team_name, team_code, today = _resolve_team_and_date(request.args)
    key = (team_code, today)
    now = time.time()

    if key in _TOTAL_CACHE and now - _TOTAL_CACHE[key][1] < CACHE_TTL_SEC:
        total = _TOTAL_CACHE[key][0]
    else:
        total = count_team_news(team_code=team_code, date=today)
        _TOTAL_CACHE[key] = (total, now)

    pages = math.ceil(total / PER_PAGE) if total else 0
    return jsonify({"count": total, "pages": pages, "per_page": PER_PAGE})
