# team_news.py
import os
import time
import datetime
import requests
from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# (선택) 로컬 윈도우 개발 편의용
try:
    from webdriver_manager.chrome import ChromeDriverManager  # noqa
except Exception:
    ChromeDriverManager = None

UA = (
    "Mozilla/5.0 (Linux; Android 10; SM-G975N) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36"
)
HDRS = {"User-Agent": UA}

# ------------------------------
# Selenium 드라이버
# ------------------------------
def _make_driver():
    opt = Options()
    opt.add_argument("--headless=new")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--disable-extensions")
    opt.add_argument(f"user-agent={UA}")
    opt.add_argument("--window-size=1280,1024")

    # Windows 로컬: webdriver-manager 사용
    if os.name == "nt" and ChromeDriverManager is not None:
        from selenium.webdriver.chrome.service import Service as Svc
        return webdriver.Chrome(service=Svc(ChromeDriverManager().install()), options=opt)

    # Linux/Railway: 환경변수 경로 사용
    opt.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    service = Service(os.getenv("CHROMEDRIVER_BIN", "/usr/bin/chromedriver"))
    return webdriver.Chrome(service=service, options=opt)

# ------------------------------
# 팀 정규화 / 코드 매핑
# ------------------------------
# 네이버 m.sports 팀코드
_CODE_MAP = {
    "SSG": "SK",
    "LG": "LG",
    "KT": "KT",
    "NC": "NC",
    "KIA": "HT",
    "삼성": "SS",
    "두산": "OB",
    "롯데": "LT",
    "한화": "HH",
    "키움": "WO",
}

# 다양한 입력 → 표준표기(네이버 팀명)으로 정규화
_ALIAS = {
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
    "kiwoom": "키움", "키움": "키움", "히어로즈": "키움", "heroes": "키움", "넥센": "키움", "woori": "키움",
    # 삼성
    "samsung": "삼성", "삼성": "삼성", "lions": "삼성",
    # NC
    "nc": "NC", "엔씨": "NC", "dinos": "NC",
    # 롯데
    "lotte": "롯데", "롯데": "롯데", "giants": "롯데",
}

def normalize_team_display(name: str | None) -> str:
    """App.js 등에서 오는 어떤 형태라도 네이버 표준표기(한글/대문자)로 정규화."""
    if not name:
        return ""
    s = str(name).strip()
    if s in _CODE_MAP:  # 이미 표준표기
        return s
    k = s.replace(" ", "").lower()
    return _ALIAS.get(k, s)  # 모르면 원본 유지

def get_team_code_map():
    """표준표기 → 네이버 팀코드 매핑 반환"""
    return dict(_CODE_MAP)

# ------------------------------
# 뉴스 수집 로직
# ------------------------------
def _news_url(team_code: str, date: str | None):
    base = f"https://m.sports.naver.com/kbaseball/news?sectionId=kbo&team={team_code}&sort=latest"
    if date:
        base += f"&date={date}"
    return base + "&isPhoto=Y"

def _extract_items_from_soup(soup: BeautifulSoup, limit=None):
    cards = soup.select("li.NewsItem_news_item__fhEmd")
    if limit:
        cards = cards[:limit]
    out = []
    for li in cards:
        a = li.select_one("a.NewsItem_link_news__tD7x3")
        if not a:
            continue

        title_tag = a.select_one("em.NewsItem_title__BXkJ6")
        title = title_tag.get_text(strip=True) if title_tag else "제목 없음"

        summary_tag = a.select_one("p[class^='NewsItem_description__']")
        summary = summary_tag.get_text(strip=True) if summary_tag else "요약 없음"

        press_tag = a.select_one("span.NewsItem_press__RJFeh")
        press = press_tag.get_text(strip=True) if press_tag else ""

        time_tag = a.select_one("span.time")
        time_str = time_tag.get_text(strip=True) if time_tag else ""

        img = a.select_one("img") or li.select_one("img")
        image = None
        if img:
            for key in ["src","data-src","data-original","data-lazy","data-thumb","data-srcset","data-lazy-src","data-echo"]:
                v = img.get(key)
                if isinstance(v, str) and v and not v.startswith("data:"):
                    image = v.strip()
                    break
            # dthumb 프록시 이미지의 실제 src 추출
            if image and "dthumb-phinf.pstatic.net" in image:
                try:
                    parsed = urlparse(image)
                    src_val = parse_qs(parsed.query).get("src", [None])[0]
                    if src_val:
                        image = unquote(src_val).strip('"')
                except Exception:
                    pass

        href = a.get("href")
        link = "https://m.sports.naver.com" + href if href else None

        out.append({
            "title": title,
            "summary": summary,
            "press": press,
            "time": time_str,
            "image": image,
            "link": link
        })
    return out

def _extract_items(html, limit=None):
    soup = BeautifulSoup(html, "html.parser")
    return _extract_items_from_soup(soup, limit)

def fetch_team_news_fast(team_code="LT", date=None, count=4):
    """셀레니움 없이 '첫 N개'만 초고속 파싱."""
    url = _news_url(team_code, date)
    r = requests.get(url, headers=HDRS, timeout=6)
    r.raise_for_status()
    return _extract_items(r.text, limit=count)

def fetch_team_news(team_code="LT", date=None, needed_count=4):
    """필요 개수만큼 스크롤 후 이미지 로딩 유도 → 재파싱."""
    drv = _make_driver()
    try:
        drv.get(_news_url(team_code, date))
        time.sleep(1.2)

        last_h = 0
        for _ in range(50):
            soup = BeautifulSoup(drv.page_source, "html.parser")
            if len(soup.select("li.NewsItem_news_item__fhEmd")) >= needed_count:
                break
            drv.execute_script("window.scrollBy(0, Math.floor(window.innerHeight*0.9));")
            time.sleep(0.35)
            h = drv.execute_script("return document.body.scrollHeight")
            if h == last_h:
                break
            last_h = h

        # 위로 올려서 첫 화면 기준으로 다시 파싱
        drv.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.05)
        return _extract_items(drv.page_source, limit=needed_count)
    finally:
        drv.quit()

def count_team_news(team_code="LT", date=None, max_scroll=80):
    """끝까지 스크롤해 카드 총 개수 카운트."""
    drv = _make_driver()
    try:
        drv.get(_news_url(team_code, date))
        time.sleep(0.9)
        last_h = 0
        for _ in range(max_scroll):
            drv.execute_script("window.scrollBy(0, Math.floor(window.innerHeight*0.95));")
            time.sleep(0.25)
            h = drv.execute_script("return document.body.scrollHeight")
            if h == last_h:
                break
            last_h = h
        soup = BeautifulSoup(drv.page_source, "html.parser")
        return len(soup.select("li.NewsItem_news_item__fhEmd"))
    finally:
        drv.quit()
