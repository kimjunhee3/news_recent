# recent.py
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def _make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,1024")
    if os.name == "nt":
        # 로컬 윈도우: 설치된 Chrome 사용(셀레니움 매니저 자동 경로)
        return webdriver.Chrome(options=opts)
    # Linux/Railway: Dockerfile에서 설치된 경로 사용
    opts.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    service = Service(os.getenv("CHROMEDRIVER_BIN", "/usr/bin/chromedriver"))
    return webdriver.Chrome(service=service, options=opts)

def fetch_recent_results(target_team):
    driver = _make_driver()
    url = "https://m.sports.naver.com/kbaseball/record/kbo?seasonCode=2025&tab=teamRank"
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[class^='TableBody_item__']"))
        )
        team_items = driver.find_elements(By.CSS_SELECTOR, "li[class^='TableBody_item__']")
        for team in team_items:
            name_el = team.find_element(By.CSS_SELECTOR, "div[class^='TeamInfo_team_name__']")
            team_name = name_el.text.strip()
            if team_name != target_team:
                continue
            result_spans = team.find_elements(By.CSS_SELECTOR, "div.ResultInfo_result__Vd3ZN > span.blind")
            results = [s.text for s in result_spans if s.text in ["승", "패", "무"]][:5]
            return results
        return []
    except Exception as e:
        print(f"❌ {target_team} 경기 결과 수집 실패:", e)
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    teams = ["한화", "LG", "롯데", "KIA", "SSG", "KT", "삼성", "NC", "두산", "키움"]
    for t in teams:
        print(f"{t}: {fetch_recent_results(t)}")
