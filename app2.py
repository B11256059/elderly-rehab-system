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
# 2. 復健運動處方定義
# ==========================================
raw_data = [
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": "50", "休息時間": "60"},
    {"器材": "大轉輪", "年齡": 70, "組數": 4, "次數": 16, "組時間": "40", "休息時間": "70"},
    {"器材": "大轉輪", "年齡": 80, "組數": 3, "次數": 13, "組時間": "35", "休息時間": "80"},
    {"器材": "大轉輪", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30", "休息時間": "90"},
    {"器材": "坐推", "年齡": 60, "組數": 5, "次數": 12, "組時間": "36", "休息時間": "60"},
    {"器材": "坐推", "年齡": 70, "組數": 5, "次數": 11, "組時間": "33", "休息時間": "70"},
    {"器材": "坐推", "年齡": 80, "組數": 4, "次數": 10, "組時間": "30", "休息時間": "80"},
    {"器材": "坐推", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30", "休息時間": "90"},
    {"器材": "漫步機", "年齡": 60, "組數": 2, "次數": "不適用", "組時間": 450, "休息時間": "60"},
    {"器材": "漫步機", "年齡": 70, "組數": 2, "次數": "不適用", "組時間": 390, "休息時間": "70"},
    {"器材": "漫步機", "年齡": 80, "組數": 2, "次數": "不適用", "組時間": 330, "休息時間": "80"},
    {"器材": "漫步機", "年齡": 90, "組數": 2, "次數": "不適用", "組時間": 300, "休息時間": "90"},
]

lookup_table = {}
for item in raw_data:
    sets = int(re.findall(r'\d+', str(item["組數"]))[0]) if "不適用" not in str(item["組數"]) else 1
    s_time = int(re.findall(r'\d+', str(item["組時間"]))[0])
    r_time = int(re.findall(r'\d+', str(item["休息時間"]))[0])
    total_m = round(((s_time * sets) + (r_time * (sets - 1))) / 60)
    lookup_table[(item["器材"], item["年齡"])] = total_m if total_m > 0 else 5

# ==========================================
# 3. 系統狀態初始化
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []
# 設定機台數量：大轉輪2、坐推3、漫步機1
if "equipment_status" not in st.session_state: 
    st.session_state.equipment_status = {
        "大轉輪_1": None, "大轉輪_2": None,
        "坐推_1": None, "坐推_2": None, "坐推_3": None,
        "漫步機_1": None
    }
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()
if "cooldown_patients" not in st.session_state: st.session_state.cooldown_patients = {}
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {}
if "form_version" not in st.session_state: st.session_state.form_version = 0

TRANSIT_COOLDOWN_SECONDS = 180
MID_PAUSE_SECONDS = 60

# ==========================================
# 4. 輔助函數
# ==========================================
def add_patient(p_id, last_name, title, age, selected_equips):
    for equip in selected_equips:
        st.session_state.waiting_queue.append({
            "id": p_id, "name": f"{last_name}{title}", "age": age,
            "target_equip": equip, "arrival_time": time.time(),
            "service_time": lookup_table.get((equip, age), 5),
            "is_paused": False, "pause_start_time": 0, "total_paused_duration": 0
        })

# ==========================================
# 5. 排程邏輯
# ==========================================
now = time.time()
need_rerun = False

for eq, p in st.session_state.equipment_status.items():
    if p:
        if p.get("is_paused", False) and (now - p["pause_start_time"] >= MID_PAUSE_SECONDS):
            p["total_paused_duration"] += MID_PAUSE_SECONDS
            p["is_paused"] = False
        if (now - p["start_time"] - p.get("total_paused_duration", 0)) / 60 >= p["service_time"]:
            st.session_state.patient_history.setdefault(p["id"], set()).add(p["target_equip"])
            st.session_state.cooldown_patients[p["id"]] = now + TRANSIT_COOLDOWN_SECONDS
            st.session_state.equipment_status[eq] = None
            need_rerun = True

if st.session_state.waiting_queue:
    busy_ids = {p["id"] for p in st.session_state.equipment_status.values() if p}
    for p in st.session_state.waiting_queue:
        wait_m = (now - p["arrival_time"]) / 60
        p["hrrn_score"] = (max(wait_m, 0.001) + p["service_time"]) / p["service_time"]
    st.session_state.waiting_queue.sort(key=lambda x: x["hrrn_score"], reverse=True)
    
    new_queue = []
    for p in st.session_state.waiting_queue:
        available_slots = [k for k, v in st.session_state.equipment_status.items() 
                           if k.startswith(p["target_equip"]) and v is None]
        if available_slots and p["id"] not in busy_ids and p["id"] not in st.session_state.cooldown_patients:
            chosen = available_slots[0]
            p["start_time"] = now
            st.session_state.equipment_status[chosen] = p
            busy_ids.add(p["id"])
            need_rerun = True
        else:
            new_queue.append(p)
    st.session_state.waiting_queue = new_queue

if need_rerun: st.rerun()

# ==========================================
# 6. UI 呈現
# ==========================================
with st.sidebar:
    if st.button("🧹 清空系統"):
        st.session_state.equipment_status = {k: None for k in st.session_state.equipment_status}
        st.session_state.waiting_queue = []
        st.rerun()

# 報到表單
with st.expander("➕ 長輩報到與處方登記", expanded=True):
    with st.form("input_form"):
        c1, c2, c3 = st.columns(3)
        ln = c1.text_input("姓氏")
        tit = c2.selectbox("稱謂", ["爺爺", "奶奶"])
        age = c3.selectbox("年齡層", [60, 70, 80, 90])
        eqs = st.multiselect("處方器材", ["大轉輪", "坐推", "漫步機"])
        if st.form_submit_button("登記"):
            p_id = f"{ln}{tit}_{age}"
            add_patient(p_id, ln, tit, age, eqs)
            st.rerun()

left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("🔴 現場排隊等待區")
    if st.session_state.waiting_queue:
        df = pd.DataFrame(st.session_state.waiting_queue)
        st.dataframe(df[["id", "name", "target_equip"]].rename(columns={"id":"編號","name":"姓名","target_equip":"器材"}), use_container_width=True)

with right_col:
    st.subheader("🟢 復健器材運作狀態區")
    for eq_name, p in st.session_state.equipment_status.items():
        if p:
            st.markdown(f"""<div class="status-card"><b>⚙️ {eq_name}</b>: {p['name']} 使用中</div>""", unsafe_allow_html=True)
            if st.button("完成", key=f"f_{eq_name}"):
                st.session_state.equipment_status[eq_name] = None
                st.rerun()
        else:
            st.markdown(f"""<div class="status-card" style="border-left: 5px solid #cbd5e1; color: #94a3b8;"><b>⚙️ {eq_name}</b><br>🟢 空閒中</div>""", unsafe_allow_html=True)

time.sleep(1)
st.rerun()