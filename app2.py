import streamlit as st
import pandas as pd
import re
import time
import random
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
# 2. 原始復健運動處方大表
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

matrix_rows = []
lookup_table = {}
for item in raw_data:
    sets = extract_number(item["組數"])
    set_time = extract_number(item["組時間"])
    rest_time = extract_number(item["休息時間"])
    total_seconds = (set_time * sets) + (rest_time * (sets - 1)) if sets > 1 else (set_time * sets)
    total_minutes = round(total_seconds / 60)
    lookup_table[(item["器材"], item["年齡"])] = total_minutes if total_minutes > 0 else 5
    matrix_rows.append({"器材名稱": item["器材"], "年齡層": f"{item['年齡']} 歲", "總時間": format_unit(total_minutes, "分")})

st.table(pd.DataFrame(matrix_rows))

# ==========================================
# 3. 系統狀態初始化
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []  
if "equipment_status" not in st.session_state: 
    st.session_state.equipment_status = {
        "大轉輪_1": None, "坐推_1": None, "坐推_2": None, "坐推_3": None, "漫步機_1": None, "漫步機_2": None
    }
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()  
if "cooldown_patients" not in st.session_state: st.session_state.cooldown_patients = {}
if "patient_id_counter" not in st.session_state: st.session_state.patient_id_counter = 1
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {}

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
    return st.session_state.patient_registry[reg_key]

def add_patient(p_id, last_name, title, age, selected_equips):
    for equip in selected_equips:
        st.session_state.waiting_queue.append({
            "id": p_id, "name": f"{last_name}{title}", "age": age,
            "target_equip": equip, "arrival_time": time.time(),
            "service_time": lookup_table.get((equip, age), 5),
            "is_paused": False, "pause_start_time": 0, "total_paused_duration": 0  
        })

# ==========================================
# 5. 側邊欄模擬 (自動注入) 與 手動登記表單
# ==========================================
with st.sidebar:
    st.header("👥 模擬情境設定")
    if st.button("🚀 啟動：長輩陸續報到模擬"):
        last_names = ["王", "陳", "林", "張", "李", "吳", "劉", "蔡", "楊", "黃", "曾", "洪", "郭", "馬", "徐", "朱", "胡", "何", "蘇", "葉"]
        equips_base = ["大轉輪", "坐推", "漫步機"]
        for i in range(20):
            ln = last_names[i % len(last_names)]
            tit = random.choice(["爺爺", "奶奶"])
            age = random.choice([60, 70, 80, 90])
            # 隨機分配 1 到 3 項器材
            eqs = random.sample(equips_base, random.randint(1, 3))
            add_patient(get_or_create_patient_id(ln, tit, age), ln, tit, age, eqs)
            time.sleep(0.3)
            st.rerun()
    
    if st.button("🧹 清空所有數據"):
        st.session_state.waiting_queue = []
        st.session_state.equipment_status = {k: None for k in st.session_state.equipment_status}
        st.session_state.cooldown_patients = {}
        st.session_state.patient_registry = {}
        st.session_state.patient_history = {}
        st.session_state.patient_id_counter = 1
        st.session_state.start_system_timestamp = time.time()
        st.rerun()

    st.write("---")
    st.header("📝 手動登記")
    with st.form("manual_reg"):
        ln = st.text_input("姓氏")
        tit = st.selectbox("稱謂", ["爺爺", "奶奶"])
        age = st.selectbox("年齡層", [60, 70, 80, 90])
        eqs = st.multiselect("復健處方器材", ["大轉輪", "坐推", "漫步機"])
        if st.form_submit_button("登記加入排程"):
            if ln and eqs:
                add_patient(get_or_create_patient_id(ln, tit, age), ln, tit, age, eqs)
                st.rerun()

# ==========================================
# 6. 主要看板內容區 (HRRN調度邏輯)
# ==========================================
st.write("---")
m1, m2, m3 = st.columns(3)
current_total_seconds = int(time.time() - st.session_state.start_system_timestamp)
m1.metric("營運總時長", f"{current_total_seconds // 3600} 時 {(current_total_seconds % 3600) // 60} 分 {current_total_seconds % 60} 秒")
m2.metric("待辦處方數", f"{len(st.session_state.waiting_queue)} 項")
now_time = time.time()
st.session_state.cooldown_patients = {k: v for k, v in st.session_state.cooldown_patients.items() if now_time < v}
m3.metric("換場休息中", f"{len(st.session_state.cooldown_patients)} 人")

# --- HRRN 核心調度 ---
now = time.time()
need_trigger_rerun = False 
for eq, p in list(st.session_state.equipment_status.items()):
    if p:
        if p.get("is_paused", False):
            if now - p["pause_start_time"] >= MID_PAUSE_SECONDS:
                p["total_paused_duration"] += MID_PAUSE_SECONDS
                p["is_paused"] = False
        elif (now - p["start_time"] - p.get("total_paused_duration", 0)) / 60 >= p["service_time"]:
            st.session_state.patient_history.setdefault(p["id"], set()).add(eq.split('_')[0])
            st.session_state.cooldown_patients[p["id"]] = now + TRANSIT_COOLDOWN_SECONDS
            st.session_state.equipment_status[eq] = None
            need_trigger_rerun = True

if st.session_state.waiting_queue:
    busy_ids = {p["id"] for p in st.session_state.equipment_status.values() if p}
    for p in st.session_state.waiting_queue:
        wait_m = (now - p["arrival_time"]) / 60
        p["hrrn_score"] = (max(wait_m, 0.001) + p["service_time"]) / p["service_time"]
    st.session_state.waiting_queue.sort(key=lambda x: x["hrrn_score"], reverse=True)
    
    rem_waiting = []
    for p in st.session_state.waiting_queue:
        available_eqs = [eq for eq, s in st.session_state.equipment_status.items() if s is None and eq.startswith(p["target_equip"])]
        if available_eqs and p["id"] not in busy_ids and p["id"] not in st.session_state.cooldown_patients:
            eq = available_eqs[0]
            p["start_time"] = now
            st.session_state.equipment_status[eq] = p
            busy_ids.add(p["id"])
            need_trigger_rerun = True
        else:
            rem_waiting.append(p)
    st.session_state.waiting_queue = rem_waiting

if need_trigger_rerun: st.rerun()

# ==========================================
# 7. 畫面呈現
# ==========================================
left_col, right_col = st.columns([1.2, 1])
with left_col:
    st.subheader("🔴 現場排隊等待區")
    if not st.session_state.waiting_queue: st.info("目前沒有長輩在排隊等待。")
    else:
        df = pd.DataFrame(st.session_state.waiting_queue)
        st.dataframe(df[["id", "name", "target_equip", "hrrn_score"]].rename(columns={"id":"ID", "name":"姓名", "target_equip":"目標", "hrrn_score":"HRRN分數"}), use_container_width=True)

with right_col:
    st.subheader("🟢 復健器材運作狀態區")
    for eq, p in st.session_state.equipment_status.items():
        if p:
            is_paused = p.get("is_paused", False)
            elapsed = int(now - p["start_time"] - p.get("total_paused_duration", 0))
            st.markdown(f"""<div class="status-card {'paused' if is_paused else ''}"><b>{eq}</b><br>👤 {p['name']} - {elapsed//60}分{elapsed%60}秒</div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if not is_paused and c1.button("⏸️ 休息", key=f"s_{eq}"): p["is_paused"]=True; p["pause_start_time"]=now; st.rerun()
            if c2.button("✅ 完成", key=f"f_{eq}"): st.session_state.equipment_status[eq]=None; st.rerun()
        else:
            st.markdown(f"""<div class="status-card" style="border-left:5px solid #cbd5e1;"><b>{eq}</b><br>🟢 空閒</div>""", unsafe_allow_html=True)

if len(st.session_state.waiting_queue) > 0 or any(p is not None for p in st.session_state.equipment_status.values()):
    time.sleep(1); st.rerun()