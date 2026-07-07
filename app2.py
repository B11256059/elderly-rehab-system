import streamlit as st
import pandas as pd
import re
import time

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
# 2. 數據與設定
# ==========================================
# 定義機台數量 (擴充點)
EQUIPMENT_CAPACITY = {
    "大轉輪": 2,
    "坐推": 3,
    "漫步機": 1
}

def get_empty_equipment_dict():
    d = {}
    for eq, count in EQUIPMENT_CAPACITY.items():
        for i in range(1, count + 1):
            d[f"{eq}_{i}"] = None
    return d

# 處方數據表
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
# 3. 初始化 Session State
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []
if "equipment_status" not in st.session_state: st.session_state.equipment_status = get_empty_equipment_dict()
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()
if "cooldown_patients" not in st.session_state: st.session_state.cooldown_patients = {}
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {}
if "form_version" not in st.session_state: st.session_state.form_version = 0

TRANSIT_COOLDOWN_SECONDS = 180
MID_PAUSE_SECONDS = 60

# ==========================================
# 4. 功能函數
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
# 5. 排程邏輯 (核心)
# ==========================================
now = time.time()
need_trigger_rerun = False

# 更新運行狀態
for eq, p in st.session_state.equipment_status.items():
    if p:
        if p.get("is_paused", False):
            if now - p["pause_start_time"] >= MID_PAUSE_SECONDS:
                p["total_paused_duration"] += MID_PAUSE_SECONDS
                p["is_paused"] = False
        
        if (now - p["start_time"] - p.get("total_paused_duration", 0)) / 60 >= p["service_time"]:
            st.session_state.patient_history.setdefault(p["id"], set()).add(p["target_equip"])
            st.session_state.cooldown_patients[p["id"]] = now + TRANSIT_COOLDOWN_SECONDS
            st.session_state.equipment_status[eq] = None
            need_trigger_rerun = True

# 分配排隊
if st.session_state.waiting_queue:
    busy_ids = {p["id"] for p in st.session_state.equipment_status.values() if p}
    for p in st.session_state.waiting_queue:
        wait_m = (now - p["arrival_time"]) / 60
        p["hrrn_score"] = (max(wait_m, 0.001) + p["service_time"]) / p["service_time"]
    
    st.session_state.waiting_queue.sort(key=lambda x: x["hrrn_score"], reverse=True)
    
    new_queue = []
    for p in st.session_state.waiting_queue:
        target_base = p["target_equip"]
        available_slots = [k for k, v in st.session_state.equipment_status.items() 
                           if k.startswith(target_base) and v is None]
        
        if available_slots and p["id"] not in busy_ids and p["id"] not in st.session_state.cooldown_patients:
            chosen = available_slots[0]
            p["start_time"] = now
            st.session_state.equipment_status[chosen] = p
            busy_ids.add(p["id"])
            need_trigger_rerun = True
        else:
            new_queue.append(p)
    st.session_state.waiting_queue = new_queue

if need_trigger_rerun: st.rerun()

# ==========================================
# 6. UI 呈現
# ==========================================
with st.sidebar:
    if st.button("🧹 清空系統"):
        st.session_state.equipment_status = get_empty_equipment_dict()
        st.session_state.waiting_queue = []
        st.session_state.patient_history = {}
        st.rerun()

left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("🔴 現場排隊區")
    if st.session_state.waiting_queue:
        df = pd.DataFrame(st.session_state.waiting_queue)
        st.dataframe(df[["id", "name", "target_equip", "hrrn_score"]].rename(columns={"id":"編號","name":"姓名","target_equip":"器材","hrrn_score":"優先分"}), use_container_width=True)

with right_col:
    st.subheader("🟢 復健機台區")
    for category in EQUIPMENT_CAPACITY.keys():
        st.markdown(f"**{category}**")
        for eq_name, p in st.session_state.equipment_status.items():
            if eq_name.startswith(category):
                if p:
                    st.markdown(f"""<div class="status-card"><b>{eq_name}</b>: {p['name']} 正在使用</div>""", unsafe_allow_html=True)
                    if st.button("完成", key=f"finish_{eq_name}"):
                        st.session_state.patient_history.setdefault(p["id"], set()).add(p["target_equip"])
                        st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
                        st.session_state.equipment_status[eq_name] = None
                        st.rerun()
                else:
                    st.info(f"{eq_name}: 空閒")

if st.session_state.waiting_queue or any(st.session_state.equipment_status.values()):
    time.sleep(1)
    st.rerun()