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

# === 3. HJNC (신항 한진) - Stale Element 에러 완벽 차단! ===
def search_hjnc(driver, target_vessel, debug_log):
    driver.delete_all_cookies()
    driver.get("about:blank")
    time.sleep(0.5)
    
    url = "https://www.hjnc.co.kr/esvc/vessel/berthScheduleT"
    results = []
    
    try:
        driver.get(url)
        time.sleep(2)
        
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
        debug_log.append("HJNC: 조회 시작")
        
        target_clean = target_vessel.replace(" ", "").upper()

        # 표 로딩 대기
        is_table_loaded = False
        for _ in range(20): 
            rows = driver.find_elements(By.CSS_SELECTOR, "div.dataTables_scrollBody table#tblMaster tbody tr")
            if len(rows) > 0:
                try:
                    first_row = rows[0].get_attribute("textContent")
                    if first_row and "조회된" not in first_row and "Loading" not in first_row and "처리중" not in first_row:
                        is_table_loaded = True
                        debug_log.append(f"HJNC: 표 완벽 로딩! (총 {len(rows)}줄)")
                        break
                except: pass
            time.sleep(1)

        # 3. 데이터 긁어오기 (5페이지)
        for page in range(1, 6):
            time.sleep(1) # 페이지 넘어가고 혹시 모를 로딩 대비 약간 쉼
            
            # [핵심] 몇 줄인지 숫자만 셈
            current_rows = driver.find_elements(By.CSS_SELECTOR, "div.dataTables_scrollBody table#tblMaster tbody tr")
            row_count = len(current_rows)
            
            # [핵심] 1번 줄, 2번 줄... 순서대로 매번 새롭게 화면에서 찾아옴 (Stale 방지)
            for i in range(row_count):
                try:
                    # i번째 줄을 매번 새로 멱살 잡기!
                    row = driver.find_elements(By.CSS_SELECTOR, "div.dataTables_scrollBody table#tblMaster tbody tr")[i]
                    
                    row_text_raw = row.get_attribute("textContent")
                    if not row_text_raw: continue
                    
                    row_text_clean = row_text_raw.replace(" ", "").upper()
                    
                    if target_clean in row_text_clean:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cols) > 10:
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
                except Exception as e:
                    # 중간에 에러가 나더라도 죽지 않고 다음 줄(i+1)로 조용히 넘어가기!
                    continue
            
            # 다음 페이지 이동
            if page < 5:
                try:
                    next_page = str(page + 1)
                    page_links = driver.find_elements(By.XPATH, f"//a[text()='{next_page}']")
                    if page_links:
                        driver.execute_script("arguments[0].click();", page_links[0])
                        time.sleep(3) # [수정] 페이지 넘어가고 조금 더 넉넉히 대기
                    else:
                        break 
                except: break

    except Exception as e:
        debug_log.append(f"HJNC 시스템 에러 발생: {e}")
        
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


