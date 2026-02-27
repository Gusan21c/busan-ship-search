import streamlit as st
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# === 브라우저 설정 (자동 감지 모드) ===
def get_driver():
    options = Options()
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    else:
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
        
        # '한달' 스위치(m1) 켜기
        driver.execute_script("""
            var monthBtn = document.querySelector('input[name="chkPeriod"][value="m1"]');
            if(monthBtn) { monthBtn.click(); }
        """)
        time.sleep(0.5)
        
        # '조회' 버튼 클릭
        driver.execute_script("""
            var btns = document.querySelectorAll('button, a, .btn');
            for(var i=0; i<btns.length; i++){
                if(btns[i].innerText && btns[i].innerText.trim() === '조회') { 
                    btns[i].click(); 
                    break; 
                }
            }
        """)
        
        target_clean = target_vessel.replace(" ", "").upper()

        # 표 로딩 대기
        time.sleep(3) 
        for _ in range(15): 
            status = driver.execute_script("""
                var rows = document.querySelectorAll('.dataTables_scrollBody table tbody tr');
                if (rows.length === 0) return 'wait';
                var text = rows[0].textContent;
                if (text.includes('Loading') || text.includes('처리중')) return 'wait';
                if (text.includes('조회된')) return 'empty';
                return 'ready';
            """)
            if status == 'ready': break
            time.sleep(1)

        # 5페이지 순회하며 데이터 긁어오기
        for page in range(1, 6):
            time.sleep(1.5) # 페이지 로딩을 위해 살짝 대기
            
            hjnc_data = driver.execute_script("""
                var results = [];
                var rows = document.querySelectorAll('.dataTables_scrollBody table tbody tr');
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
            
            if hjnc_data:
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
            
            # [핵심 수정] 선생님이 찾아주신 'page-link' 클래스로 다음 페이지 클릭!
            if page < 5:
                next_page = str(page + 1)
                clicked = driver.execute_script(f"""
                    var links = document.querySelectorAll('a.page-link');
                    for(var i=0; i<links.length; i++) {{
                        if(links[i].textContent.trim() === '{next_page}') {{
                            links[i].click(); 
                            return true;
                        }}
                    }}
                    return false;
                """)
                if not clicked: 
                    break # 다음 페이지(예: 3페이지)가 없으면 더 이상 찾지 않고 종료
                time.sleep(2) # 버튼 누르고 다음 페이지 표가 뜰 때까지 2초 대기

    except Exception: pass
        
    unique = []
    seen = set()
    for r in results:
        key = r['모선명'] + r['접안일시']
        if key not in seen: 
            seen.add(key)
            unique.append(r)
    return unique

# === 2. DGT (동원글로벌터미널) - 표 경로 완벽 수정본 ===
def search_dgt(driver, target_vessel):
    driver.delete_all_cookies()
    driver.get("about:blank")
    time.sleep(0.5)
    
    url = "https://info.dgtbusan.com/DGT/esvc/vessel/berthScheduleT"
    results = []
    
    try:
        driver.get(url)
        # 접속하자마자 표가 뜨므로, 굳이 '조회' 버튼을 누를 필요가 없습니다.
        
        target_clean = target_vessel.replace(" ", "").upper()

        # 표 로딩 대기
        time.sleep(3) 
        for _ in range(15): 
            # [핵심 수정] 껍데기(.dataTables_scrollBody) 빼고, 진짜 표(#tblMaster)만 찾습니다!
            status = driver.execute_script("""
                var rows = document.querySelectorAll('#tblMaster tbody tr');
                if (rows.length === 0) return 'wait';
                var text = rows[0].textContent;
                if (text.includes('Loading') || text.includes('처리중')) return 'wait';
                if (text.includes('조회된') || text.includes('없습니다')) return 'empty';
                return 'ready';
            """)
            if status == 'ready': break
            time.sleep(1)

        # 5페이지 순회하며 데이터 긁어오기
        for page in range(1, 6):
            time.sleep(1.5)
            
            # [핵심 수정] 여기서도 #tblMaster 로 경로를 확실하게 수정했습니다.
            dgt_data = driver.execute_script("""
                var results = [];
                var rows = document.querySelectorAll('#tblMaster tbody tr');
                for(var i=0; i<rows.length; i++) {
                    var cols = rows[i].querySelectorAll('td');
                    // DGT는 배 이름이 3번(4번째 칸), 접안일시가 5번(6번째 칸)에 있습니다.
                    if(cols.length > 5) {
                        results.push({
                            v_voyage: cols[2].textContent.trim(), 
                            v_name: cols[3].textContent.trim(),   
                            v_date: cols[5].textContent.trim(),   
                            full_text: rows[i].textContent.toUpperCase()
                        });
                    }
                }
                return results;
            """)
            
            if dgt_data:
                for r in dgt_data:
                    if target_clean in r['full_text'].replace(" ", ""):
                        if target_clean in r['v_name'].replace(" ", "").upper():
                            results.append({
                                "터미널": "DGT (동원글로벌터미널)",
                                "구분": "신항",
                                "모선명": r['v_name'],
                                "터미널항차": r['v_voyage'],
                                "접안일시": r['v_date'],
                                "선사항차": "-" 
                            })
            
            # 다음 페이지 이동
            if page < 5:
                next_page = str(page + 1)
                clicked = driver.execute_script(f"""
                    var links = document.querySelectorAll('a.page-link');
                    for(var i=0; i<links.length; i++) {{
                        if(links[i].textContent.trim() === '{next_page}') {{
                            links[i].click(); 
                            return true;
                        }}
                    }}
                    return false;
                """)
                if not clicked: 
                    break 
                time.sleep(2)

    except Exception: pass
        
    unique = []
    seen = set()
    for r in results:
        key = r['모선명'] + r['접안일시']
        if key not in seen: 
            seen.add(key)
            unique.append(r)
    return unique

# === 3. PNIT (부산국제신항) ===
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def search_pnit(driver, target_vessel):
    driver.delete_all_cookies()
    driver.get("about:blank")
    time.sleep(0.5)
    
    url = "https://www.pnitl.com/infoservice/vessel/vslScheduleList.jsp"
    results = []
    
    try:
        driver.get(url)
        
        # 1. 로딩 대기: '종료일' 칸이 화면에 뜰 때까지 눈 부릅뜨고 최대 10초 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "strEdDate"))
        )
        
        # 2. 30일 뒤 날짜 계산
        from datetime import datetime, timedelta
        target_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # 3. 날짜 강제 주입 및 인식시키기
        driver.execute_script(f"""
            var edDate = document.getElementById('strEdDate');
            if(edDate) {{
                edDate.value = '{target_date}';
                edDate.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)
        time.sleep(1) # 날짜 세팅 후 잠시 숨 고르기
        
        # 4. [핵심] 진짜 사람처럼 마우스로 돋보기 버튼 찌르기!
        search_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "submitbtn"))
        )
        # 로봇 시야에 버튼이 들어오도록 화면 스크롤 맞추기
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_btn)
        time.sleep(0.5)
        
        try:
            # 진짜 마우스 클릭 (매크로 차단 회피)
            search_btn.click() 
        except:
            # 혹시라도 막히면 강제 클릭
            driver.execute_script("arguments[0].click();", search_btn)
            
        # 5. 검색 버튼을 눌렀으니, 30일치 데이터가 날아와서 표가 다시 그려질 때까지 5초 대기
        time.sleep(5) 
        
        target_clean = target_vessel.replace(" ", "").upper()

        # 6. 데이터 싹쓸이
        pnit_data = driver.execute_script("""
            var results = [];
            var rows = document.querySelectorAll('.tblType_08 table tbody tr');
            for(var i=0; i<rows.length; i++) {
                var cols = rows[i].querySelectorAll('td');
                if(cols.length > 8) {
                    results.push({
                        v_voyage: cols[2].textContent.trim(), 
                        v_line_voyage: cols[3].textContent.trim(),
                        v_name: cols[5].textContent.trim(),   
                        v_date: cols[8].textContent.trim(),   
                        full_text: rows[i].textContent.toUpperCase()
                    });
                }
            }
            return results;
        """)
        
        if pnit_data:
            for r in pnit_data:
                if target_clean in r['full_text'].replace(" ", ""):
                    if target_clean in r['v_name'].replace(" ", "").upper():
                        results.append({
                            "터미널": "PNIT (부산국제신항)",
                            "구분": "신항",
                            "모선명": r['v_name'],
                            "터미널항차": r['v_voyage'],
                            "접안일시": r['v_date'],
                            "선사항차": r['v_line_voyage']
                        })

    except Exception as e: 
        # 에러가 나더라도 프로그램이 죽지 않고 조용히 넘어가게 처리
        pass
        
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
st.markdown("**[신항] 터미널 동시 검색**")

with st.form("search"):
    c1, c2 = st.columns([3, 1])
    with c1:
        vessel_input = st.text_input("모선명", value="")
    with c2:
        st.write("")
        st.write("")
        btn = st.form_submit_button("🔍 통합 조회 시작", type="primary")

if btn:
    if not vessel_input:
        st.warning("배 이름을 입력해주세요!")
    else:
        status = st.status(f"'{vessel_input}' 신항 조회 중...", expanded=True)
        try:
            driver = get_driver()
            all_res = []
            
           # 1. HJNC 검색 실행 & 결과 합치기
            status.write("📍 HJNC (한진신항) 수색 중...")
            all_res.extend(search_hjnc(driver, vessel_input))
            
            # 2. DGT 검색 실행 & 결과 합치기
            status.write("📍 DGT (동원글로벌) 수색 중...")
            all_res.extend(search_dgt(driver, vessel_input))

            # 3. PNIT 검색 실행 & 결과 합치기
            status.write("📍 PNIT (부산국제) 수색 중...")
            all_res.extend(search_pnit(driver, vessel_input))
            
            driver.quit()
            status.update(label="조회 완료!", state="complete", expanded=False)
            
            if all_res:
                # 날짜순으로 정렬
                all_res.sort(key=lambda x: x['접안일시'])
                st.success(f"✅ 총 {len(all_res)}건 발견")
                for i, res in enumerate(all_res):
                    # 터미널별로 색깔 다르게 주기
                    if "HJNC" in res['터미널']: 
                        color = "orange"
                    elif "DGT" in res['터미널']: 
                        color = "violet" # DGT는 보라색으로 구분
                    elif "PNIT" in res['터미널']: 
                        color = "red" # PNIT는 빨간색으로 구분
                    else: 
                        color = "gray"
                    
                    st.markdown(f"### {i+1}. :{color}[{res['터미널']} - {res['구분']}]")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("모선명", res['모선명'])
                    c2.metric("입항예정일시(ETA)", res['접안일시'])
                    c3.metric("터미널 모선항차", res['터미널항차'])
                    
                    if res.get('선사항차') and res.get('선사항차') != "-":
                        st.caption(f"선사 항차: {res['선사항차']}")
                        
                    st.divider()
            else:
                st.error(f"'{vessel_input}'에 대한 결과가 신항(HJNC, DGT, PNIT)에 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
