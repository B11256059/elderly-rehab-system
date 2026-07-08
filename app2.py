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
    .waiting-row { font-size: 0.9em; padding: 10px; border-bottom: 1px solid #e2e8f0; }
    .highlight-text { color: #0e7490; font-weight: bold; }
    .warning-text { color: #b45309; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 智慧復健動態排程管理系統")

# ==========================================
# 2. 原始復健運動處方大表
# ==========================================
st.subheader("📋 復健運動處方大表")

raw_data = [
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": "50 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 70, "組數": 4, "次數": 16, "組時間": "40 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 80, "組數": 3, "次數": 13, "組時間": "35 (AI推估)", "休息時間": "80 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "90 (參考ACSM)"},
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
    total_seconds = (set_time * sets) + (rest_time * (sets - 1)) if sets > 1 else set_time * sets
    total_minutes = round(total_seconds / 60)
    lookup_table[(item["器材"], item["年齡"])] = total_minutes if total_minutes > 0 else 5
    matrix_rows.append({
        "器材名稱": item["器材"], "年齡層": f"{item['年齡']} 歲",
        "次數": format_unit(item["次數"], "次"), "組數": format_unit(item["組數"], "組"),
        "組時間": format_unit(item["組時間"], "秒"), "休息時間": format_unit(item["休息時間"], "秒"),
        "總時間": format_unit(total_minutes, "分")
    })

st.table(pd.DataFrame(matrix_rows))

# ==========================================
# 3. 系統狀態初始化 (已修正器材數量)
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []  
if "equipment_status" not in st.session_state: 
    # 配置：大轉輪 1 台、漫步機 2 台
    st.session_state.equipment_status = {
        "大轉輪_1": None, 
        "漫步機_1": None, "漫步機_2": None
    }
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
# 4. 功能函數
# ==========================================
def get_or_create_patient_id(last_name, title, age):
    reg_key = (last_name, title, age)
    if reg_key not in st.session_state.patient_registry:
        p_id = f"#{st.session_state.patient_id_counter:03d}"
        st.session_state.patient_registry[reg_key] = p_id
        st.session_state.patient_id_counter += 1
    else:
        p_id = st.session_state.patient_registry[reg_key]
    return p_id

def add_patient(p_id, last_name, title, age, selected_equips):
    for equip in selected_equips:
        st.session_state.waiting_queue.append({
            "id": p_id, "name": f"{last_name}{title}", "age": age,
            "target_equip": equip, "arrival_time": time.time(),
            "service_time": lookup_table.get((equip, age), 5),
            "is_paused": False, "pause_start_time": 0, "total_paused_duration": 0 
        })

# ==========================================
# 5. 側邊欄模擬與控制
# ==========================================
with st.sidebar:
    st.header("👥 模擬情境")
    if st.button("🚀 注入 20 位長輩數據"):
        mock_list = [("王", "爺爺", 70, ["大轉輪", "漫步機"]), ("陳", "奶奶", 60, ["漫步機"])] * 10
        for ln_m, tit_m, age_m, eqs_m in mock_list:
            p_id_m = get_or_create_patient_id(ln_m, tit_m, age_m)
            add_patient(p_id_m, ln_m, tit_m, age_m, eqs_m)
        st.rerun()
    
    if st.button("🧹 清空所有數據"):
        st.session_state.waiting_queue = []
        st.session_state.equipment_status = {eq: None for eq in st.session_state.equipment_status.keys()}
        st.session_state.cooldown_patients = {}
        st.session_state.patient_registry = {}
        st.session_state.patient_history = {}
        st.session_state.patient_id_counter = 1
        st.session_state.start_system_timestamp = time.time()
        st.rerun()

# ==========================================
# 6. 主要看板與調度邏輯
# ==========================================
st.write("---")
m1, m2, m3 = st.columns(3)
m1.metric("營運總時長", f"{int(time.time() - st.session_state.start_system_timestamp)//60} 分")
m2.metric("待辦處方數", f"{len(st.session_state.waiting_queue)} 項")
m3.metric("換場休息中", f"{len(st.session_state.cooldown_patients)} 人")

with st.expander("➕ 長輩報到", expanded=True):
    with st.form(key="patient_input_form"):
        col1, col2, col3 = st.columns(3)
        input_ln = col1.text_input("姓氏")
        input_tit = col2.selectbox("稱謂", ["爺爺", "奶奶"])
        input_age = col3.selectbox("年齡層", [60, 70, 80, 90])
        input_equips = st.multiselect("復健處方器材", ["大轉輪", "漫步機"])
        if st.form_submit_button("進入排隊"):
            p_id = get_or_create_patient_id(input_ln, input_tit, input_age)
            add_patient(p_id, input_ln, input_tit, input_age, input_equips)
            st.rerun()

# 調度核心
now = time.time()
for eq, p in list(st.session_state.equipment_status.items()):
    if p:
        if p.get("is_paused") and (now - p["pause_start_time"] >= MID_PAUSE_SECONDS):
            p["total_paused_duration"] += MID_PAUSE_SECONDS
            p["is_paused"] = False
        if not p.get("is_paused") and (now - p["start_time"] - p.get("total_paused_duration", 0)) / 60 >= p["service_time"]:
            st.session_state.cooldown_patients[p["id"]] = now + TRANSIT_COOLDOWN_SECONDS
            st.session_state.equipment_status[eq] = None

for p in st.session_state.waiting_queue[:]:
    busy_ids = {p["id"] for p in st.session_state.equipment_status.values() if p}
    available_eqs = [eq for eq, status in st.session_state.equipment_status.items() if status is None and eq.startswith(p["target_equip"])]
    if available_eqs and p["id"] not in busy_ids and p["id"] not in st.session_state.cooldown_patients:
        st.session_state.equipment_status[available_eqs[0]] = {**p, "start_time": now}
        st.session_state.waiting_queue.remove(p)

# ==========================================
# 7. 前端呈現 (已修正渲染邏輯)
# ==========================================
left_col, right_col = st.columns([1.5, 1])
with left_col:
    st.subheader("🔴 現場排隊等待區")
    if st.session_state.waiting_queue:
        st.table(pd.DataFrame(st.session_state.waiting_queue)[["id", "name", "target_equip"]])
    else:
        st.info("目前沒有長輩在排隊等待。")

with right_col:
    st.subheader("🟢 器材狀態")
    for eq, p in st.session_state.equipment_status.items():
        if p:
            st.warning(f"{eq}: {p['name']} 執行中")
            if st.button(f"中斷 {eq}", key=f"pause_{eq}"):
                p["is_paused"] = True
                p["pause_start_time"] = time.time()
                st.rerun()
        else:
            st.success(f"{eq}: 空閒")

if any(st.session_state.equipment_status.values()) or st.session_state.waiting_queue:
    time.sleep(1)
    st.rerun()