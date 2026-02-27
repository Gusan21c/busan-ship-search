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
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except: pass
        
    return driver

# === 1. HJNC (신항 한진) ===
def search_hjnc(driver, target_vessel):
    driver.delete_all_cookies()
    driver.get("about:blank")
    time.sleep(0.5)
    
    url = "https://www.hjnc.co.kr/esvc/vessel/berthScheduleT"
    results = []
    
    try:
        driver.get(url)
        time.sleep(2)
        
        # '한달' & '조회' 버튼 강제 클릭
        try:
            driver.execute_script("""
                var radios = document.querySelectorAll('input[type="radio"]');
                if(radios.length > 2) { radios[2].click(); }
                
                var btns = document.querySelectorAll('button, a, .btn');
                for(var i=0; i<btns.length; i++){
                    if(btns[i].innerText && btns[i].innerText.trim() === '조회') { 
                        btns[i].click(); 
                        break; 
                    }
                }
            """)
        except: pass
        
        target_clean = target_vessel.replace(" ", "").upper()

        # 표 로딩 대기
        for _ in range(20): 
            rows = driver.find_elements(By.CSS_SELECTOR, "div.dataTables_scrollBody table#tblMaster tbody tr")
            if len(rows) > 0:
                first_row = rows[0].get_attribute("textContent")
                if first_row and "조회된" not in first_row and "Loading" not in first_row and "처리중" not in first_row:
                    break
            time.sleep(1)

        # 5페이지 순회하며 데이터 긁어오기
        for page in range(1, 6):
            rows = driver.find_elements(By.CSS_SELECTOR, "div.dataTables_scrollBody table#tblMaster tbody tr")
            
            for row in rows:
                # 눈에 보이지 않는 스크롤 안쪽 글자까지 추출
                row_text_raw = row.get_attribute("textContent")
                if not row_text_raw: continue
                
                row_text_clean = row_text_raw.replace(" ", "").upper()
                
                if target_clean in row_text_clean:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) > 10:
                        try:
                            # 4:선박명 / 3:모선항차 / 10:입항일시 / 5:선사항차
                            v_name = cols[4].get_attribute("textContent").strip()
                            v_voyage = cols[3].get_attribute("textContent").strip()
                            v_date = cols[10].get_attribute("textContent").strip()
                            v_line_voyage = cols[5].get_attribute("textContent").strip()
                            
                            if target_clean in v_name.replace(" ", "").upper():
                                results.append({
                                    "터미널": "HJNC (신항 한진)",
                                    "구분": "신항",
                                    "모선명": v_name,
                                    "터미널항차": v_voyage,
                                    "접안일시": v_date,
                                    "선사항차": v_line_voyage
                                })
                        except: continue
            
            # 다음 페이지 이동
            if page < 5:
                try:
                    next_page = str(page + 1)
                    page_links = driver.find_elements(By.XPATH, f"//a[text()='{next_page}']")
                    if page_links:
                        driver.execute_script("arguments[0].click();", page_links[0])
                        time.sleep(2)
                    else:
                        break 
                except: break

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
st.set_page_config(page_title="신항 통합 조회", page_icon="🚢", layout="wide")
st.title("🚢 신항 통합 모선 조회")

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
            
            status.write("📍 HJNC(신항 한진) 조회 중...")
            all_res.extend(search_hjnc(driver, vessel_input))
            
            driver.quit()
            status.update(label="완료!", state="complete", expanded=False)
            
            if all_res:
                all_res.sort(key=lambda x: x['접안일시'])
                st.success(f"총 {len(all_res)}건 발견")
                for i, res in enumerate(all_res):
                    color = "orange" # 신항은 주황색 포인트
                    st.markdown(f"### {i+1}. :{color}[{res['터미널']} - {res['구분']}]")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("모선명", res['모선명'])
                    c2.metric("접안 일시", res['접안일시'])
                    c3.metric("터미널 모선항차", res['터미널항차'])
                    
                    # 신항은 선사항차 정보가 있으니 밑에 작게 표시해줍니다.
                    if res.get('선사항차') and res.get('선사항차') != "-":
                        st.caption(f"선사 항차: {res['선사항차']}")
                        
                    st.divider()
            else:
                st.error(f"'{vessel_input}' 결과가 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
