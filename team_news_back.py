# team_news_back.py
from flask import Blueprint, render_template, request, jsonify
from team_news import (
    fetch_team_news, fetch_team_news_fast, get_team_code_map,
    count_team_news, normalize_team_display
)
import datetime, time, math

PER_PAGE = 4
CACHE_TTL_SEC = 600
FAST_TTL_SEC = 120

news_bp = Blueprint("news", __name__, template_folder="templates")

_TOTAL_CACHE: dict[tuple[str, str], tuple[int, float]] = {}
_FIRST4_CACHE: dict[tuple[str, str], tuple[list, float]] = {}

def _resolve_team_and_date(args):
    # 1) team 쿼리를 정규화(영문/별칭 → 표준표기)
    raw_name = args.get("team", "롯데")
    team_name = normalize_team_display(raw_name) or "롯데"

    # 2) 코드 매핑
    code_map = get_team_code_map()
    team_code = code_map.get(team_name, "LT")

    today = datetime.datetime.now().strftime("%Y%m%d")
    return team_name, team_code, today

@news_bp.route("/news")
def index():
    team_name, team_code, today = _resolve_team_and_date(request.args)
    key = (team_code, today)
    now = time.time()

    if key in _FIRST4_CACHE and now - _FIRST4_CACHE[key][1] < FAST_TTL_SEC:
        first4 = _FIRST4_CACHE[key][0]
    else:
        first4 = fetch_team_news_fast(team_code=team_code, date=today, count=PER_PAGE)
        if len(first4) < PER_PAGE:
            first4 = fetch_team_news(team_code=team_code, date=today, needed_count=PER_PAGE)
        _FIRST4_CACHE[key] = (first4, now)

    return render_template(
        "team_news.html",
        team_name=team_name,   # 템플릿/JS가 API 호출할 때 그대로 사용
        news_list=first4,
        current_page=1
    )

@news_bp.route("/api/news")
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

@news_bp.route("/api/news_total")
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

