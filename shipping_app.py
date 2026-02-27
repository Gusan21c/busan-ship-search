import streamlit as st
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# === 브라우저 설정 ===
def get_driver():
    options = Options()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    chromium_path = None
    chromedriver_path = None
    possible_bins = ["/usr/bin/chromium", "/usr/bin/chromium-browser"]
    possible_drivers = ["/usr/bin/chromedriver", "/usr/lib/chromium-browser/chromedriver"]
    
    for p in possible_bins:
        if os.path.exists(p): chromium_path = p; break
    for d in possible_drivers:
        if os.path.exists(d): chromedriver_path = d; break
            
    if chromium_path and chromedriver_path:
        options.binary_location = chromium_path
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            driver = webdriver.Chrome(service=service, options=options)
        except:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        
    return driver

# === 1. 허치슨 (북항 - 건드리지 않음) ===
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
        if key not in seen: seen.add(key); unique.append(r)
    return unique

# === 2. BPT (북항 - 건드리지 않음) ===
def search_bpt(driver, target_vessel, debug_log):
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
            driver.execute_script("""
                var btns = document.querySelectorAll('img, a, button');
                for(var i=0; i<btns.length; i++) {
                    if(btns[i].alt && btns[i].alt.includes('조회')) { btns[i].click(); return; }
                    if(btns[i].innerText && btns[i].innerText.includes('조회')) { btns[i].click(); return; }
                }
            """)
        except Exception as e: pass
        time.sleep(2)

        try:
            driver.switch_to.frame("output")
            for _ in range(10):
                rows = driver.find_elements(By.TAG_NAME, "tr")
                if len(rows) > 10: break
                time.sleep(1)
        except: pass

        rows = driver.find_elements(By.TAG_NAME, "tr")
        target_clean = target_vessel.replace(" ", "").upper()
        
        for row in rows:
            if "선박명" in row.text: continue
            row_text_clean = row.text.replace(" ", "").upper()
            
            if target_clean in row_text_clean:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) > 6:
                    try:
                        v_name = cols[3].text.strip()
                        v_date = cols[6].text.strip()
                        v_voyage = cols[2].text.strip()
                        if not v_date.startswith("20"): continue
                        results.append({
                            "터미널": "BPT (부산항터미널)",
                            "구분": cols[0].text.strip(),
                            "모선명": v_name,
                            "터미널항차": v_voyage,
                            "접안일시": v_date,
                            "선사항차": "-" 
                        })
                    except: continue
    except: pass
    finally:
        driver.switch_to.default_content()
        
    unique = []
    seen = set()
    for r in results:
        key = r['모선명'] + r['접안일시']
        if key not in seen: seen.add(key); unique.append(r)
    return unique

# === 3. HJNC (신항 한진) - 완벽 수정판! ===
def search_hjnc(driver, target_vessel, debug_log):
    driver.delete_all_cookies()
    driver.get("about:blank")
    time.sleep(0.5)
    
    url = "https://www.hjnc.co.kr/esvc/vessel/berthScheduleT"
    results = []
    
    try:
        driver.get(url)
        time.sleep(2)
        
        # 1. '한달' 옵션 및 '조회' 버튼 아주 강력하게 강제 클릭
        driver.execute_script("""
            // 3번째 라디오 버튼('한달') 클릭
            var radios = document.querySelectorAll('input[type="radio"]');
            if(radios.length > 2) { radios[2].click(); }
            
            // '조회' 글자가 포함된 버튼 무조건 클릭
            var btns = document.querySelectorAll('button, a, .btn');
            for(var i=0; i<btns.length; i++){
                if(btns[i].innerText && btns[i].innerText.trim() === '조회') { 
                    btns[i].click(); 
                    break; 
                }
            }
        """)
        debug_log.append("HJNC: '한달' 셋팅 및 '조회' 버튼 클릭 완료")
        
        target_clean = target_vessel.replace(" ", "").upper()

        # 2. [핵심] 표가 온전히 뜰 때까지 눈 부릅뜨고 대기
        is_table_loaded = False
        for _ in range(20): # 최대 20초 넉넉하게 기다림
            # 선생님이 알려주신 tblMaster를 집중 타격!
            rows = driver.find_elements(By.CSS_SELECTOR, "#tblMaster tbody tr")
            if len(rows) > 0:
                first_row = rows[0].text
                # 아직 로딩 중이거나 텅 빈 메시지가 아니면 표가 뜬 것!
                if "조회된" not in first_row and "Loading" not in first_row and "처리중" not in first_row:
                    is_table_loaded = True
                    debug_log.append(f"HJNC: tblMaster 표 로딩 완벽 성공! (총 {len(rows)}줄 확인)")
                    break
            time.sleep(1)

        # 3. 데이터 긁어오기 (5페이지 순회)
        for page in range(1, 6):
            # 매 페이지마다 표 다시 읽기
            rows = driver.find_elements(By.CSS_SELECTOR, "#tblMaster tbody tr")
            
            for row in rows:
                row_text_clean = row.text.replace(" ", "").upper()
                
                # 배 이름이 포함된 줄을 찾으면
                if target_clean in row_text_clean:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) > 10:
                        try:
                            # 선생님 캡처본 기준 칸 번호
                            # 4:선박명 / 3:모선항차 / 10:입항일시 / 5:선사항차
                            v_name = cols[4].text.strip()
                            v_voyage = cols[3].text.strip()
                            v_date = cols[10].text.strip()
                            v_line_voyage = cols[5].text.strip()
                            
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
                    # 하단의 1, 2, 3... 페이지 링크 클릭
                    page_links = driver.find_elements(By.XPATH, f"//a[text()='{next_page}']")
                    if page_links and page_links[0].is_displayed():
                        driver.execute_script("arguments[0].click();", page_links[0])
                        time.sleep(2) # 페이지 넘어가고 2초 대기
                    else:
                        break # 페이지 끝
                except: break

    except Exception as e:
        debug_log.append(f"HJNC 에러 발생: {e}")
        
    unique = []
    seen = set()
    for r in results:
        key = r['모선명'] + r['접안일시']
        if key not in seen: seen.add(key); unique.append(r)
    return unique

# === UI ===
st.set_page_config(page_title="부산항 통합 조회", page_icon="🚢", layout="wide")
st.title("🚢 부산항(북항+신항) 통합 조회기")
st.markdown("**[북항]** 허치슨, BPT / **[신항]** HJNC (한진) 동시 검색")

with st.form("search"):
    c1, c2 = st.columns([3, 1])
    with c1:
        vessel_input = st.text_input("모선명 (Vessel Name)", value="")
    with c2:
        st.write("")
        st.write("")
        btn = st.form_submit_button("🔍 전체 조회 시작", type="primary")

if btn:
    if not vessel_input:
        st.warning("배 이름을 입력해주세요!")
    else:
        status = st.status(f"'{vessel_input}' 추적 중...", expanded=True)
        try:
            driver = get_driver()
            all_res = []
            debug_logs = []
            
            status.write("📍 허치슨(북항) 수색 중...")
            all_res.extend(search_hktl(driver, vessel_input))
            
            status.write("📍 BPT(북항) 수색 중...")
            all_res.extend(search_bpt(driver, vessel_input, debug_logs))
            
            status.write("📍 HJNC(신항 한진) 수색 중...")
            all_res.extend(search_hjnc(driver, vessel_input, debug_logs))
            
            driver.quit()
            status.update(label="조회 완료!", state="complete", expanded=False)
            
            with st.expander("🛠️ 시스템 작동 로그 (디버깅용)"):
                for log in debug_logs:
                    st.text(f"- {log}")
            
            if all_res:
                all_res.sort(key=lambda x: x['접안일시'])
                st.success(f"✅ 총 {len(all_res)}건의 일정을 찾았습니다.")
                
                for i, res in enumerate(all_res):
                    if "HJNC" in res['터미널']: color = "orange"
                    elif "BPT" in res['터미널']: color = "blue"
                    else: color = "green"
                    
                    st.markdown(f"### {i+1}. :{color}[{res['터미널']} - {res['구분']}]")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("모선명", res['모선명'])
                    c2.metric("입항예정일시(ETA)", res['접안일시'])
                    c3.metric("터미널 모선항차", res['터미널항차'])
                    if res.get('선사항차') and res.get('선사항차') != "-":
                        st.caption(f"선사 항차: {res['선사항차']}")
                    st.divider()
            else:
                st.error(f"'{vessel_input}' 스케줄을 찾지 못했습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
