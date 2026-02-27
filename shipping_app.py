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

# === 1. 허치슨 (북항) - 이상 없음 ===
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

# === 2. BPT (북항) - 원상 복구 & 자바스크립트 무적 추출 ===
def search_bpt(driver, target_vessel, debug_log):
    driver.delete_all_cookies()
    driver.get("about:blank")
    time.sleep(0.5)
    
    url = "https://info.bptc.co.kr/content/sw/frame/berth_status_text_frame_sw_kr.jsp?p_id=BETX_SH_KR&snb_num=2&snb_div=service"
    results = []
    try:
        driver.get(url)
        time.sleep(2)
        
        # 옵션 세팅
        try:
            driver.execute_script("document.querySelectorAll('input[type=radio]')[2].click();") 
            sort_labels = driver.find_elements(By.XPATH, "//*[contains(text(), '입항예정일시')]")
            for label in sort_labels: driver.execute_script("arguments[0].click();", label)
        except: pass
        time.sleep(0.5)

        # 조회 버튼 강제 클릭
        try:
            driver.execute_script("""
                var btns = document.querySelectorAll('img, a, button');
                for(var i=0; i<btns.length; i++) {
                    if(btns[i].alt && btns[i].alt.includes('조회')) { btns[i].click(); return; }
                    if(btns[i].innerText && btns[i].innerText.includes('조회')) { btns[i].click(); return; }
                }
            """)
            debug_log.append("BPT: 조회 버튼 클릭 완료")
        except: pass
        time.sleep(2)

        # 프레임 진입 및 표 로딩 확인
        try:
            driver.switch_to.frame("output")
            for _ in range(10):
                row_count = driver.execute_script("return document.querySelectorAll('tr').length;")
                if row_count > 10:
                    debug_log.append(f"BPT: 표 완벽 로딩! (총 {row_count}줄)")
                    break
                time.sleep(1)
        except Exception as e:
            debug_log.append(f"BPT 프레임 에러: {e}")

        # [핵심] 브라우저 내부에서 데이터 싹쓸이 (에러 방지)
        try:
            bpt_data = driver.execute_script("""
                var results = [];
                var rows = document.querySelectorAll('tr');
                for(var i=0; i<rows.length; i++) {
                    var cols = rows[i].querySelectorAll('td');
                    if(cols.length > 6) {
                        results.push({
                            term_div: cols[0].textContent.trim(),
                            v_voyage: cols[2].textContent.trim(),
                            v_name: cols[3].textContent.trim(),
                            v_date: cols[6].textContent.trim(),
                            full_text: rows[i].textContent.toUpperCase()
                        });
                    }
                }
                return results;
            """)
            
            target_clean = target_vessel.replace(" ", "").upper()
            for r in bpt_data:
                if "선박명" in r['full_text']: continue
                if target_clean in r['full_text'].replace(" ", ""):
                    if target_clean in r['v_name'].replace(" ", "").upper():
                        if r['v_date'].startswith("20"):
                            results.append({
                                "터미널": "BPT (부산항터미널)",
                                "구분": r['term_div'],
                                "모선명": r['v_name'],
                                "터미널항차": r['v_voyage'],
                                "접안일시": r['v_date'],
                                "선사항차": "-" 
                            })
        except Exception as e:
            debug_log.append(f"BPT 데이터 파싱 에러: {e}")

    except Exception as e:
        debug_log.append(f"BPT 전체 에러: {e}")
    finally:
        driver.switch_to.default_content()
        
    unique = []
    seen = set()
    for r in results:
        key = r['모선명'] + r['접안일시']
        if key not in seen: seen.add(key); unique.append(r)
    return unique

# === 3. HJNC (신항 한진) - 자바스크립트 무적 추출 ===
def search_hjnc(driver, target_vessel, debug_log):
    driver.delete_all_cookies()
    driver.get("about:blank")
    time.sleep(0.5)
    
    url = "https://www.hjnc.co.kr/esvc/vessel/berthScheduleT"
    results = []
    
    try:
        driver.get(url)
        time.sleep(2)
        
        # '한달' 및 '조회' 클릭
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

        # 표 로딩 넉넉히 대기
        is_table_loaded = False
        for _ in range(20): 
            row_count = driver.execute_script("return document.querySelectorAll('#tblMaster tbody tr').length;")
            if row_count > 0:
                first_row = driver.execute_script("return document.querySelector('#tblMaster tbody tr').textContent;")
                if first_row and "조회된" not in first_row and "Loading" not in first_row and "처리중" not in first_row:
                    is_table_loaded = True
                    debug_log.append(f"HJNC: 표 완벽 로딩! (총 {row_count}줄)")
                    break
            time.sleep(1)

        # 5페이지 순회
        for page in range(1, 6):
            time.sleep(1)
            
            # [핵심] 로봇이 헤매지 않게 브라우저 내부에서 JS로 데이터를 몽땅 훔쳐옵니다 (Stale 에러 원천 차단)
            try:
                hjnc_data = driver.execute_script("""
                    var results = [];
                    var rows = document.querySelectorAll('#tblMaster tbody tr');
                    for(var i=0; i<rows.length; i++) {
                        var cols = rows[i].querySelectorAll('td');
                        if(cols.length > 10) {
                            results.push({
                                v_voyage: cols[3].textContent.trim(),
                                v_name: cols[4].textContent.trim(),
                                v_line_voyage: cols[5].textContent.trim(),
                                v_date: cols[10].textContent.trim(),
                                full_text: rows[i].textContent.toUpperCase()
                            });
                        }
                    }
                    return results;
                """)
                
                # 가져온 데이터 파이썬에서 정리
                for r in hjnc_data:
                    if target_clean in r['full_text'].replace(" ", ""):
                        if target_clean in r['v_name'].replace(" ", "").upper():
                            results.append({
                                "터미널": "HJNC (신항 한진)",
                                "구분": "신항",
                                "모선명": r['v_name'],
                                "터미널항차": r['v_voyage'],
                                "접안일시": r['v_date'],
                                "선사항차": r['v_line_voyage']
                            })
            except Exception as e:
                debug_log.append(f"HJNC {page}페이지 추출 에러: {e}")
            
            # 다음 페이지 클릭
            if page < 5:
                next_page = str(page + 1)
                click_success = driver.execute_script(f"""
                    var links = document.querySelectorAll('.paginate_button');
                    for(var i=0; i<links.length; i++) {{
                        if(links[i].textContent.trim() === '{next_page}') {{
                            links[i].click();
                            return true;
                        }}
                    }}
                    var a_tags = document.querySelectorAll('a');
                    for(var i=0; i<a_tags.length; i++) {{
                        if(a_tags[i].textContent.trim() === '{next_page}') {{
                            a_tags[i].click();
                            return true;
                        }}
                    }}
                    return false;
                """)
                
                if click_success:
                    debug_log.append(f"HJNC: {next_page}페이지로 이동")
                    time.sleep(3) 
                else:
                    break 

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
