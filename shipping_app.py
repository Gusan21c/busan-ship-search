import streamlit as st
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === 브라우저 설정 (자동 감지 모드) ===
def get_driver():
    options = Options()
    options.add_argument("--headless") # 화면 없이 실행 (필수)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # [중요] 클라우드 환경인지 확인하는 로직
    # Streamlit Cloud에는 '/usr/bin/chromium'에 브라우저가 설치됩니다.
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        # 패키지로 설치된 드라이버를 직접 지정
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # 내 컴퓨터(Windows)에서는 다운로드 방식 사용
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
    return driver

# === 1. 허치슨 ===
def search_hktl(driver, target_vessel):
    url = "https://custom.hktl.com/jsp/T01/sunsuk.jsp"
    results = []
    try:
        driver.get(url)
        time.sleep(1)
        if len(driver.find_elements(By.TAG_NAME, "tr")) < 5:
            frames = driver.find_elements(By.TAG_NAME, "frame") + driver.find_elements(By.TAG_NAME, "iframe")
            for frame in frames:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    if len(driver.find_elements(By.TAG_NAME, "tr")) > 5: break
                except: continue

        for page in range(1, 6):
            time.sleep(0.5)
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 12: continue
                if "DEPARTURE" in row.text: continue
                if "모선명" in row.text: continue
                
                try:
                    v_name = cols[11].text.strip()
                    if target_vessel.replace(" ", "").upper() in v_name.replace(" ", "").upper():
                        results.append({
                            "터미널": "HKTL (허치슨)",
                            "구분": "자성대/신감만",
                            "모선명": v_name,
                            "터미널항차": cols[0].text.strip(),
                            "접안일시": cols[4].text.strip(),
                            "선사항차": cols[1].text.strip()
                        })
                except: continue
            if page < 5:
                try:
                    next_page = page + 1
                    links = driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        if link.text.strip() in [str(next_page), f"[{next_page}]"]:
                            link.click()
                            break
                except: break
    except: pass
    
    unique = []
    seen = set()
    for r in results:
        key = r['모선명'] + r['접안일시']
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

# === 2. BPT ===
def search_bpt(driver, target_vessel):
    driver.delete_all_cookies()
    driver.get("about:blank")
    time.sleep(0.5)
    
    url = "https://info.bptc.co.kr/content/sw/frame/berth_status_text_frame_sw_kr.jsp?p_id=BETX_SH_KR&snb_num=2&snb_div=service"
    results = []
    
    try:
        driver.get(url)
        time.sleep(2)
        
        try:
            driver.execute_script("document.querySelectorAll('input[type=radio]')[2].click();") 
            sort_labels = driver.find_elements(By.XPATH, "//*[contains(text(), '입항예정일시')]")
            for label in sort_labels: driver.execute_script("arguments[0].click();", label)
        except: pass
        time.sleep(0.5)

        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            if inputs:
                target_box = inputs[-1]
                target_box.click()
                target_box.send_keys(Keys.ENTER)
        except: pass
        
        time.sleep(3)
        try:
            driver.switch_to.frame("output")
        except: pass

        rows = driver.find_elements(By.TAG_NAME, "tr")
        target_clean = target_vessel.replace(" ", "").upper()
        
        for row in rows:
            row_text_clean = row.text.replace(" ", "").upper()
            if target_clean in row_text_clean:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) > 6 and "202" in row.text:
                    found_date = ""
                    found_vessel = ""
                    found_term_voy = ""
                    
                    for idx, col in enumerate(cols):
                        txt = col.text.strip()
                        if txt.startswith("202") and len(txt) > 10 and not found_date:
                            found_date = txt
                        if target_clean in txt.replace(" ", "").upper():
                            found_vessel = txt
                        if idx == 2:
                            found_term_voy = txt
                    
                    if found_date:
                        results.append({
                            "터미널": "BPT (부산항터미널)",
                            "구분": cols[0].text.strip(),
                            "모선명": found_vessel if found_vessel else target_vessel,
                            "터미널항차": found_term_voy,
                            "접안일시": found_date,
                            "선사항차": "-" 
                        })
        
        driver.switch_to.default_content()

    except Exception: pass
    
    unique = []
    seen = set()
    for r in results:
        key = r['모선명'] + r['접안일시']
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

# === UI ===
st.set_page_config(page_title="부산항 통합 조회", page_icon="🚢", layout="wide")
st.title("🚢 부산항 통합 모선 조회")

with st.form("search"):
    c1, c2 = st.columns([3, 1])
    with c1:
        vessel_input = st.text_input("모선명", value="")
    with c2:
        st.write("")
        st.write("")
        btn = st.form_submit_button("🔍 조회 시작", type="primary")

if btn:
    if not vessel_input:
        st.warning("배 이름을 입력해주세요!")
    else:
        status = st.status(f"'{vessel_input}' 조회 중...", expanded=True)
        try:
            driver = get_driver()
            all_res = []
            
            status.write("📍 허치슨 조회 중...")
            all_res.extend(search_hktl(driver, vessel_input))
            
            status.write("📍 BPT 조회 중...")
            all_res.extend(search_bpt(driver, vessel_input))
            
            driver.quit()
            status.update(label="완료!", state="complete", expanded=False)
            
            if all_res:
                all_res.sort(key=lambda x: x['접안일시'])
                st.success(f"총 {len(all_res)}건 발견")
                for i, res in enumerate(all_res):
                    color = "blue" if "BPT" in res['터미널'] else "green"
                    st.markdown(f"### {i+1}. :{color}[{res['터미널']} - {res['구분']}]")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("모선명", res['모선명'])
                    c2.metric("접안 일시", res['접안일시'])
                    c3.metric("터미널 모선항차", res['터미널항차'])
                    st.divider()
            else:
                st.error(f"'{vessel_input}' 결과가 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
