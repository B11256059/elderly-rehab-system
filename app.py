import streamlit as st
import pandas as pd
import re
import time

# ==========================================
# 1. 網頁基本設定
# ==========================================
st.set_page_config(page_title="高齡復健運動處方與動態排程系統", layout="wide")
st.title("高齡復健運動處方與動態排程系統")

# ==========================================
# 2. 原始資料庫與原本精美表格的處理
# ==========================================
raw_data = [
    # 器材一: 大轉輪
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": "50 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 70, "組數": 4, "次數": 16, "組時間": "40 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 80, "組數": 3, "次數": 13, "組時間": "35 (AI推估)", "休息時間": "80 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "90 (參考ACSM)"},
    
    # 器材二: 坐推
    {"器材": "坐推", "年齡": 60, "組數": 5, "次數": 12, "組時間": "36 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "坐推", "年齡": 70, "組數": 5, "次數": 11, "組時間": "33 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "坐推", "年齡": 80, "組數": 4, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "80 (參考ACSM)"},
    {"器材": "坐推", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "90 (參考ACSM)"},
    
    # 器材三: 漫步機
    {"器材": "漫步機", "年齡": 60, "組數": 2, "次數": "不適用", "組時間": 450, "休息時間": "60 (參考ACSM)"},
    {"器材": "漫步機", "年齡": 70, "組數": 2, "次數": "不適用", "組時間": 390, "休息時間": "70 (參考ACSM)"},
    {"器材": "漫步機", "年齡": 80, "組數": 2, "次數": "不適用", "組時間": 330, "休息時間": "80 (參考ACSM)"},
    {"器材": "漫步機", "年齡": 90, "組數": 2, "次數": "不適用", "組時間": 300, "休息時間": "90 (參考ACSM)"},
]

def format_unit(value, unit):
    val_str = str(value).strip()
    if val_str == "" or val_str == "0": return f"- {unit}"
    if unit in val_str or "不適用" in val_str: return val_str
    for tag in ["(AI推估)", "(參考ACSM)"]:
        if tag in val_str:
            clean_num = val_str.replace(tag, "").strip()
            return f"{clean_num} {unit} {tag}"
    return f"{val_str} {unit}"

def extract_number(value):
    val_str = str(value).strip()
    if "不適用" in val_str: return 0
    numbers = re.findall(r'\d+', val_str)
    return int(numbers[0]) if numbers else 0

matrix_rows = []
lookup_table = {}

for item in raw_data:
    sets = extract_number(item["組數"])
    set_time = extract_number(item["組時間"])
    rest_time = extract_number(item["休息時間"])
    
    if sets > 1:
        total_seconds = (set_time * sets) + (rest_time * (sets - 1))
    else:
        total_seconds = set_time * sets
        
    total_minutes = round(total_seconds / 60)
    display_total = str(total_minutes) if total_seconds > 0 else ""
    lookup_table[(item["器材"], item["年齡"])] = total_minutes

    matrix_rows.append({
        "器材名稱": item["器材"],
        "年齡層": f"{item['年齡']} 歲",
        "次數": format_unit(item["次數"], "次"),
        "組數": format_unit(item["組數"], "組"),
        "組時間": format_unit(item["組時間"], "秒"),
        "休息時間": format_unit(item["休息時間"], "秒"),
        "總時間": format_unit(display_total, "分")
    })

st.subheader("復健運動處方大表")
df_prescription = pd.DataFrame(matrix_rows)
st.table(df_prescription)

# ==========================================
# 3. 實務動態排程與系統狀態初始化
# ==========================================
if "waiting_queue" not in st.session_state:
    st.session_state.waiting_queue = []  
if "equipment_status" not in st.session_state:
    st.session_state.equipment_status = {"大轉輪": None, "坐推": None, "漫步機": None}
if "start_system_timestamp" not in st.session_state:
    st.session_state.start_system_timestamp = time.time()  

# 【新增狀態】用於記錄長輩從器材下來後的換場休息時間 (Key: (name, age), Value: 結束時的時間戳)
if "cooldown_patients" not in st.session_state:
    st.session_state.cooldown_patients = {}

# 定義換場休息時間：3 分鐘 (AI推估)
TRANSIT_COOLDOWN_MINUTES = 3
TRANSIT_COOLDOWN_SECONDS = TRANSIT_COOLDOWN_MINUTES * 60

# 計算總秒數，並精準換算為 時、分、秒 格式
current_total_seconds = int(time.time() - st.session_state.start_system_timestamp)
display_hours = current_total_seconds // 3600
display_mins = (current_total_seconds % 3600) // 60
display_secs = current_total_seconds % 60

system_time_text = f"{display_hours} 小時 {display_mins} 分鐘 {display_secs} 秒"

st.write("---")
st.subheader("復健場域智能化排程看板")

# 檢查現場有沒有人（排隊中、運動中、或處於換場休息中）
has_active_patients = (
    len(st.session_state.waiting_queue) > 0 
    or any(p is not None for p in st.session_state.equipment_status.values())
    or any(time.time() < end_t for end_t in st.session_state.cooldown_patients.values())
)

# 前端控制面板
cmd_col, timer_col = st.columns([1, 1])

with cmd_col:
    with st.expander("長輩報到", expanded=True):
        p_name = st.text_input("姓名", value="", placeholder="例如：王小明")
        p_age = st.selectbox("年齡層", ["請選擇...", 60, 70, 80, 90], format_func=lambda x: f"{x} 歲" if isinstance(x, int) else x)
        p_equip = st.selectbox("需復健器材", ["請選擇...", "大轉輪", "坐推", "漫步機"])
        
        if st.button("進入排隊等待"):
            if not p_name.strip():
                st.error("⚠️ 請輸入姓名！")
            elif p_age == "請選擇...":
                st.error("⚠️ 請選擇年齡層！")
            elif p_equip == "請選擇...":
                st.error("⚠️ 請選擇需復健器材！")
            else:
                allocated_time = lookup_table.get((p_equip, p_age), 5)
                new_patient = {
                    "name": p_name.strip(),
                    "age": p_age,
                    "equipment": p_equip,
                    "arrival_real_time": time.time(),     
                    "total_exercise_time": allocated_time
                }
                st.session_state.waiting_queue.append(new_patient)
                st.success(f"【{p_name}】已進入排隊等待！目標【{p_equip}】，處方總時長 {allocated_time} 分鐘。")
                st.rerun()

with timer_col:
    st.markdown(f"### 系統營運總時間：`{system_time_text}`")
    st.caption(f"💡 換場移轉休息時間已設為 `{TRANSIT_COOLDOWN_MINUTES} 分鐘` (AI推估)")
    if has_active_patients:
        st.info("⚡ 智能化分流調度中...")
    else:
        st.info("🟢 目前場內全空，系統定時器【靜止中】，等待下一位長輩進入。")

# ==========================================
# 4. HRRN 排程與狀態更新核心邏輯
# ==========================================
# 4-1. 處理正在運動的人：個別計算時間，做完自動釋放並進入換場休息鎖
for eq, patient in list(st.session_state.equipment_status.items()):
    if patient is not None:
        elapsed = int((time.time() - patient["start_real_time"]) // 60)
        remaining = patient["total_exercise_time"] - elapsed
        if remaining <= 0:
            st.toast(f"【{patient['name']}】已完成【{eq}】復健！開始換場休息 3 分鐘。")
            # 【關鍵修改】完工時，將該長輩加入冷卻倒數清單
            p_key = (patient["name"], patient["age"])
            st.session_state.cooldown_patients[p_key] = time.time() + TRANSIT_COOLDOWN_SECONDS
            st.session_state.equipment_status[eq] = None  

# 4-2. 根據 HRRN 演算法分配閒置器材給排隊的人（加入「姓名+年齡」防重疊鎖與「離機休息鎖」）
if st.session_state.waiting_queue:
    # 獲取當前正在使用器材的長輩
    busy_patients = {(p["name"], p["age"]) for p in st.session_state.equipment_status.values() if p is not None}
    
    queue_data = []
    for p in st.session_state.waiting_queue:
        wait_m = int((time.time() - p["arrival_real_time"]) // 60)
        score = (wait_m + p["total_exercise_time"]) / p["total_exercise_time"]
        
        p_copy = p.copy()
        p_copy['waiting_time'] = wait_m
        p_copy['priority_score'] = score
        queue_data.append(p_copy)
        
    df_queue = pd.DataFrame(queue_data)
    df_queue = df_queue.sort_values(by='priority_score', ascending=False)
    
    still_waiting = []
    for p_dict in df_queue.to_dict(orient='records'):
        target_eq = p_dict['equipment']
        p_name = p_dict['name']
        p_age = p_dict['age']
        p_key = (p_name, p_age)
        
        # 檢查該長輩是否還在離機換場冷卻時間內
        is_in_cooldown = False
        if p_key in st.session_state.cooldown_patients:
            if time.time() < st.session_state.cooldown_patients[p_key]:
                is_in_cooldown = True
            else:
                # 時間到了，自動移除冷卻狀態
                del st.session_state.cooldown_patients[p_key]
        
        # 關鍵判定：器材空閒、長輩目前沒在用其他器材、且「已經離機換場休息滿 3 分鐘」
        if st.session_state.equipment_status[target_eq] is None and p_key not in busy_patients and not is_in_cooldown:
            p_dict['start_real_time'] = time.time() 
            st.session_state.equipment_status[target_eq] = p_dict        
            busy_patients.add(p_key)
            st.toast(f"【{p_dict['name']}（{p_age}歲）】換場休息結束，開始使用【{target_eq}】！")
        else:
            clean_p = {k: p_dict[k] for k in ["name", "age", "equipment", "arrival_real_time", "total_exercise_time"]}
            still_waiting.append(clean_p)
            
    st.session_state.waiting_queue = still_waiting

# ==========================================
# 5. 前端實時看板呈現（排隊區 vs 執行區）
# ==========================================
view_col1, view_col2 = st.columns(2)

with view_col1:
    st.markdown("### 🔴 現場排隊等待區")
    if st.session_state.waiting_queue:
        disp_queue = []
        for p in st.session_state.waiting_queue:
            total_wait_sec = int(time.time() - p["arrival_real_time"])
            wait_min = total_wait_sec // 60
            wait_sec = total_wait_sec % 60
            hrrn_score = (wait_min + p["total_exercise_time"]) / p["total_exercise_time"]
            
            p_key = (p["name"], p["age"])
            is_busy = p_key in {(x["name"], x["age"]) for x in st.session_state.equipment_status.values() if x is not None}
            
            # 【更新前端標記】讓管理人員知道長輩卡在排隊區是因為「正在別台動」還是「剛下來在換場休息」
            if is_busy:
                status_tag = " 正在使用其他器材"
            elif p_key in st.session_state.cooldown_patients and time.time() < st.session_state.cooldown_patients[p_key]:
                rem_cd = int(st.session_state.cooldown_patients[p_key] - time.time())
                status_tag = f" 換場休息 (剩 {rem_cd} 秒)"
            else:
                status_tag = ""
            
            disp_queue.append({
                "姓名": f"{p['name']}{status_tag}",
                "年齡": f"{p['age']}歲",
                "目標器材": p["equipment"],
                "處方總時間": f"{p['total_exercise_time']} 分鐘",
                "等待時間": f"{wait_min}分 {wait_sec}秒",
                "HRRN優先權分數": hrrn_score
            })
            
        df_wait_disp = pd.DataFrame(disp_queue)
        df_wait_disp = df_wait_disp.sort_values(by='HRRN優先權分數', ascending=False)
        st.dataframe(df_wait_disp.style.format({"HRRN優先權分數": "{:.2f}"}), use_container_width=True, hide_index=True)
    else:
        st.info("🟢 目前沒有長輩在排隊等待。")

with view_col2:
    st.markdown("### 🟢 復健器材運作狀態區")
    
    eq_data = []
    for eq, patient in st.session_state.equipment_status.items():
        if patient is not None:
            total_exe_sec = int(time.time() - patient["start_real_time"])
            exe_min = total_exe_sec // 60
            exe_sec = total_exe_sec % 60
            
            rem_sec = (patient["total_exercise_time"] * 60) - total_exe_sec
            rem_min = max(0, rem_sec // 60)
            rem_sec = max(0, rem_sec % 60)
            
            eq_data.append({
                "復健器材": eq,
                "當前使用者": f"{patient['name']} ({patient['age']}歲)",
                "當前狀態": "🔴 使用中",
                "已執行時間": f"{exe_min}分 {exe_sec}秒",
                "剩餘時間": f"{rem_min}分 {rem_sec}秒"
            })
        else:
            eq_data.append({
                "復健器材": eq,
                "當前使用者": "－",
                "當前狀態": "🟢 空閒中",
                "已執行時間": "－",
                "剩餘時間": "－"
            })
            
    df_eq_disp = pd.DataFrame(eq_data)
    st.table(df_eq_disp)

# ==========================================
# 6. 動態刷新驅動
# ==========================================
if has_active_patients:
    time.sleep(1.0)  
    st.rerun()