import streamlit as st
import pandas as pd
import re
import time
from datetime import datetime

# ==========================================
# 1. 網頁基本設定與美化 CSS
# ==========================================
st.set_page_config(page_title="智慧復健動態排程系統", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    .status-card {
        background-color: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #10b981;
        margin-bottom: 20px;
    }
    .status-card.paused {
        border-left: 5px solid #eab308;
        background-color: #fefce8;
    }
    .highlight-text { color: #0e7490; font-weight: bold; }
    .warning-text { color: #b45309; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 智慧復健動態排程管理系統")

# ==========================================
# 2. 定義器材配置 (修改點：定義數量)
# ==========================================
EQUIP_CONFIG = {"大轉輪": 2, "坐推": 3, "漫步機": 1}
ALL_EQUIP_UNITS = []
for name, count in EQUIP_CONFIG.items():
    for i in range(1, count + 1):
        ALL_EQUIP_UNITS.append(f"{name}-{i}")

# ==========================================
# 3. 復健運動處方大表 (原始邏輯保留)
# ==========================================
st.subheader("📋 復健運動處方大表")
raw_data = [
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": "50 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 70, "組數": 4, "次數": 16, "組時間": "40 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 80, "組數": 3, "次數": 13, "組時間": "35 (AI推估)", "休息時間": "80 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "90 (參考ACSM)"},
    {"器材": "坐推", "年齡": 60, "組數": 5, "次數": 12, "組時間": "36 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "坐推", "年齡": 70, "組數": 5, "次數": 11, "組時間": "33 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "坐推", "年齡": 80, "組數": 4, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "80 (參考ACSM)"},
    {"器材": "坐推", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "90 (參考ACSM)"},
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

lookup_table = {}
matrix_rows = []
for item in raw_data:
    sets = extract_number(item["組數"])
    set_time = extract_number(item["組時間"])
    rest_time = extract_number(item["休息時間"])
    total_seconds = (set_time * sets) + (rest_time * (sets - 1)) if sets > 1 else set_time * sets
    total_minutes = round(total_seconds / 60)
    # 存入 lookup 時將 "大轉輪-1" 統一還原為 "大轉輪" 去對應表
    base_equip_name = item["器材"]
    lookup_table[(base_equip_name, item["年齡"])] = total_minutes if total_minutes > 0 else 5
    matrix_rows.append({"器材名稱": item["器材"], "年齡層": f"{item['年齡']} 歲", "次數": format_unit(item["次數"], "次"), "組數": format_unit(item["組數"], "組"), "組時間": format_unit(item["組時間"], "秒"), "休息時間": format_unit(item["休息時間"], "秒"), "總時間": format_unit(str(total_minutes) if total_seconds > 0 else "", "分")})

st.table(pd.DataFrame(matrix_rows))

# ==========================================
# 4. 系統狀態初始化 (修改點：設備字典初始化)
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []  
if "equipment_status" not in st.session_state: 
    st.session_state.equipment_status = {eq: None for eq in ALL_EQUIP_UNITS}
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()  
if "cooldown_patients" not in st.session_state: st.session_state.cooldown_patients = {}
if "patient_id_counter" not in st.session_state: st.session_state.patient_id_counter = 1
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {}
if "input_last_name" not in st.session_state: st.session_state.input_last_name = ""
if "input_equips" not in st.session_state: st.session_state.input_equips = []
if "form_version" not in st.session_state: st.session_state.form_version = 0
if "form_status" not in st.session_state: st.session_state.form_status = {"type": None, "msg": None}

TRANSIT_COOLDOWN_SECONDS = 180 
MID_PAUSE_SECONDS = 60

# ==========================================
# 5. 功能函數
# ==========================================
def get_or_create_patient_id(last_name, title, age):
    reg_key = (last_name, title, age)
    if reg_key not in st.session_state.patient_registry:
        p_id = f"#{st.session_state.patient_id_counter:03d}"
        st.session_state.patient_registry[reg_key] = p_id
        st.session_state.patient_id_counter += 1
    return st.session_state.patient_registry[reg_key]

def add_patient(p_id, last_name, title, age, selected_equips):
    for equip in selected_equips:
        base_name = equip.split('-')[0] # 獲取類別
        st.session_state.waiting_queue.append({
            "id": p_id, "name": f"{last_name}{title}", "age": age,
            "target_equip": equip, 
            "base_name": base_name, # 紀錄類別以便防重
            "arrival_time": time.time(),
            "service_time": lookup_table.get((base_name, age), 5),
            "original_service_time": lookup_table.get((base_name, age), 5),
            "is_paused": False,          
            "pause_start_time": 0,      
            "total_paused_duration": 0  
        })

# ==========================================
# 6. 側邊欄模擬 (保留完整邏輯)
# ==========================================
with st.sidebar:
    st.header("👥 模擬情境")
    if st.button("🚀 注入 20 位長輩數據"):
        mock_list = [("王", "爺爺", 70, ["大轉輪-1", "坐推-1"]), ("陳", "奶奶", 60, ["坐推-2", "漫步機-1"])]
        for ln_m, tit_m, age_m, eqs_m in mock_list:
            p_id_m = get_or_create_patient_id(ln_m, tit_m, age_m)
            add_patient(p_id_m, ln_m, tit_m, age_m, eqs_m)
        st.rerun()
    
    if st.button("🧹 清空所有數據"):
        st.session_state.waiting_queue = []
        st.session_state.equipment_status = {eq: None for eq in ALL_EQUIP_UNITS}
        st.session_state.cooldown_patients = {}
        st.session_state.patient_registry = {}
        st.session_state.patient_history = {}
        st.session_state.patient_id_counter = 1
        st.rerun()

# ==========================================
# 7. 報到表單 (修改點：加入防重邏輯)
# ==========================================
with st.expander("➕ 長輩報到與處方登記", expanded=True):
    with st.form(key="patient_input_form"):
        col1, col2, col3 = st.columns(3)
        input_ln = col1.text_input("姓氏", value=st.session_state.input_last_name)
        input_tit = col2.selectbox("稱謂", ["爺爺", "奶奶"])
        input_age = col3.selectbox("年齡層", [60, 70, 80, 90])
        input_equips = st.multiselect("復健處方器材 (含編號)", ALL_EQUIP_UNITS)
        
        if st.form_submit_button("進入排隊"):
            # 防重複機制：比對 "類別 (base_name)"
            current_waiting_bases = [p["base_name"] for p in st.session_state.waiting_queue]
            current_using_bases = [eq.split('-')[0] for eq, p in st.session_state.equipment_status.items() if p]
            
            invalid = [eq for eq in input_equips if eq.split('-')[0] in (current_waiting_bases + current_using_bases)]
            
            if invalid:
                st.error(f"❌ 登記失敗：該類別 ({', '.join(invalid)}) 已在排隊或使用中！")
            else:
                p_id = get_or_create_patient_id(input_ln.strip(), input_tit, input_age)
                add_patient(p_id, input_ln.strip(), input_tit, input_age, input_equips)
                st.rerun()

# ==========================================
# 8. HRRN 調度邏輯
# ==========================================
now = time.time()
need_rerun = False

# 器材釋放邏輯
for eq, p in st.session_state.equipment_status.items():
    if p:
        if p.get("is_paused"):
            if now - p["pause_start_time"] >= MID_PAUSE_SECONDS:
                p["total_paused_duration"] += MID_PAUSE_SECONDS
                p["is_paused"] = False
        
        if (now - p["start_time"] - p.get("total_paused_duration", 0)) / 60 >= p["service_time"]:
            st.session_state.equipment_status[eq] = None
            need_rerun = True

# 排隊配對
for p in st.session_state.waiting_queue[:]:
    if st.session_state.equipment_status.get(p["target_equip"]) is None:
        p["start_time"] = now
        st.session_state.equipment_status[p["target_equip"]] = p
        st.session_state.waiting_queue.remove(p)
        need_rerun = True

if need_rerun: st.rerun()

# ==========================================
# 9. 前端看板 (顯示器材與排隊)
# ==========================================
st.write("---")
l_col, r_col = st.columns([1.2, 1])
with l_col:
    st.subheader("🔴 現場排隊等待區")
    if st.session_state.waiting_queue:
        df = pd.DataFrame(st.session_state.waiting_queue)
        st.dataframe(df[["id", "name", "target_equip"]].rename(columns={"id":"ID", "name":"姓名", "target_equip":"目標器材"}), hide_index=True)
with r_col:
    st.subheader("🟢 復健器材運作狀態區")
    for eq, p in st.session_state.equipment_status.items():
        if p:
            st.markdown(f'<div class="status-card"><b>⚙️ {eq}</b><br>👤 使用者: {p["name"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-card" style="border-left: 5px solid #cbd5e1;"><b>⚙️ {eq}</b><br>🟢 空閒</div>', unsafe_allow_html=True)

time.sleep(1)
st.rerun()