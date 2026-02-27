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
    options.add_argument("--headless") # 화면 없이 실행
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
        
        # [수정 완결판] '한달' 라벨 글자를 직접 찾아서 정확히 클릭!
        driver.execute_script("""
            var labels = document.querySelectorAll('label');
            for(var i=0; i<labels.length; i++) {
                if(labels[i].innerText.includes('한달')) {
                    labels[i].click();
                    break;
                }
            }
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
        time.sleep(3) # 검색 후 넉넉히 대기
        for _ in range(15): 
            # 선생님이 확인해주신 경로 적용!
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
            time.sleep(1)
            
            # [핵심] 자바스크립트로 화면 안쪽 데이터 통째로 훔쳐오기
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
            
            # 파이썬에서 배 이름 매칭
            if hjnc_data:
                for r in hjnc_data:
                    # 띄어쓰기 싹 무시하고 대문자로 완벽 비교
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
            
            # 다음 페이지 이동
            if page < 5:
                next_page = str(page + 1)
                clicked = driver.execute_script(f"""
                    var links = document.querySelectorAll('.paginate_button');
                    for(var i=0; i<links.length; i++) {{
                        if(links[i].textContent.trim() === '{next_page}') {{
                            links[i].click(); return true;
                        }}
                    }}
                    return false;
                """)
                if not clicked: break # 더 이상 넘길 페이지가 없으면 종료
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

# === UI ===
st.set_page_config(page_title="신항 통합 조회", page_icon="🚢", layout="wide")
st.title("🚢 신항 통합 모선 조회")
st.markdown("**[신항] HJNC(한진) 터미널 조회**")

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
        status = st.status(f"'{vessel_input}' 신항 조회 중...", expanded=True)
        try:
            driver = get_driver()
            all_res = []
            
            status.write("📍 HJNC(신항 한진) 스캔 중...")
            all_res.extend(search_hjnc(driver, vessel_input))
            
            driver.quit()
            status.update(label="조회 완료!", state="complete", expanded=False)
            
            if all_res:
                all_res.sort(key=lambda x: x['접안일시'])
                st.success(f"✅ 총 {len(all_res)}건 발견")
                for i, res in enumerate(all_res):
                    color = "orange"
                    st.markdown(f"### {i+1}. :{color}[{res['터미널']} - {res['구분']}]")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("모선명", res['모선명'])
                    c2.metric("입항일시 (ETA)", res['접안일시'])
                    c3.metric("터미널 모선항차", res['터미널항차'])
                    
                    if res.get('선사항차') and res.get('선사항차') != "-":
                        st.caption(f"선사 항차: {res['선사항차']}")
                        
                    st.divider()
            else:
                st.error(f"'{vessel_input}'에 대한 결과가 신항(HJNC)에 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
