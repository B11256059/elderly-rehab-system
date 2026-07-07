import streamlit as st
import pandas as pd
import re
import time

# ==========================================
# 1. 網頁基本設定與美化
# ==========================================
st.set_page_config(page_title="智慧復健動態排程系統", layout="wide")

st.markdown("""
    <style>
    .status-card { background-color: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid #10b981; margin-bottom: 10px; }
    .status-card.paused { border-left: 5px solid #eab308; background-color: #fefce8; }
    .highlight-text { color: #0e7490; font-weight: bold; }
    .warning-text { color: #b45309; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 智慧復健動態排程管理系統 (多機台版)")

# ==========================================
# 2. 數據與設定
# ==========================================
lookup_table = {("大轉輪", 60): 5, ("大轉輪", 70): 4, ("大轉輪", 80): 3, ("大轉輪", 90): 3,
                ("坐推", 60): 5, ("坐推", 70): 5, ("坐推", 80): 4, ("坐推", 90): 3,
                ("漫步機", 60): 8, ("漫步機", 70): 7, ("漫步機", 80): 6, ("漫步機", 90): 5}

# 系統狀態
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []
if "equipment_status" not in st.session_state:
    st.session_state.equipment_status = {
        "大轉輪": [None, None],        # 2 台
        "坐推": [None, None, None],    # 3 台
        "漫步機": [None]               # 1 台
    }
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {}
if "cooldown_patients" not in st.session_state: st.session_state.cooldown_patients = {}
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()
if "patient_id_counter" not in st.session_state: st.session_state.patient_id_counter = 1

TRANSIT_COOLDOWN_SECONDS = 180
MID_PAUSE_SECONDS = 60

# ==========================================
# 3. 核心邏輯
# ==========================================
def add_patient(last_name, title, age, selected_equips):
    p_id = f"#{st.session_state.patient_id_counter:03d}"
    st.session_state.patient_id_counter += 1
    for equip in selected_equips:
        st.session_state.waiting_queue.append({
            "id": p_id, "name": f"{last_name}{title}", "age": age,
            "target_equip": equip, "arrival_time": time.time(),
            "service_time": lookup_table.get((equip, age), 5),
            "is_paused": False, "pause_start_time": 0, "total_paused_duration": 0
        })

# --- 調度引擎 ---
now = time.time()
need_rerun = False

# 1. 檢查運作中機台是否結束
for eq_name, slots in st.session_state.equipment_status.items():
    for i, p in enumerate(slots):
        if p:
            if p.get("is_paused"):
                if (now - p["pause_start_time"]) >= MID_PAUSE_SECONDS:
                    p["total_paused_duration"] += MID_PAUSE_SECONDS
                    p["is_paused"] = False
            
            active_sec = now - p["start_time"] - p.get("total_paused_duration", 0)
            if active_sec / 60 >= p["service_time"]:
                st.session_state.patient_history.setdefault(p["id"], set()).add(eq_name)
                st.session_state.cooldown_patients[p["id"]] = now + TRANSIT_COOLDOWN_SECONDS
                st.session_state.equipment_status[eq_name][i] = None
                need_rerun = True

# 2. 處理排隊分配
if st.session_state.waiting_queue:
    busy_ids = {p["id"] for slots in st.session_state.equipment_status.values() for p in slots if p}
    # HRRN 分數計算
    for p in st.session_state.waiting_queue:
        wait_m = max((now - p["arrival_time"]) / 60, 0.001)
        p["hrrn_score"] = (wait_m + p["service_time"]) / p["service_time"]
    
    st.session_state.waiting_queue.sort(key=lambda x: x["hrrn_score"], reverse=True)
    
    still_waiting = []
    for p in st.session_state.waiting_queue:
        eq = p["target_equip"]
        is_cd = p["id"] in st.session_state.cooldown_patients
        
        assigned = False
        if not is_cd and p["id"] not in busy_ids:
            for i, slot in enumerate(st.session_state.equipment_status[eq]):
                if slot is None:
                    p["start_time"] = now
                    st.session_state.equipment_status[eq][i] = p
                    busy_ids.add(p["id"])
                    assigned = True
                    need_rerun = True
                    break
        if not assigned: still_waiting.append(p)
    st.session_state.waiting_queue = still_waiting

if need_rerun: st.rerun()

# ==========================================
# 4. 介面呈現
# ==========================================
with st.sidebar:
    if st.button("🧹 清空系統"):
        st.session_state.clear()
        st.rerun()

col1, col2 = st.columns(2)
with col1:
    st.subheader("🔴 現場排隊等待")
    if st.session_state.waiting_queue:
        df = pd.DataFrame(st.session_state.waiting_queue)
        st.dataframe(df[["id", "name", "target_equip", "hrrn_score"]], use_container_width=True)
    else: st.info("無人排隊")

with col2:
    st.subheader("🟢 器材運作狀態")
    for eq, slots in st.session_state.equipment_status.items():
        st.write(f"**{eq}**")
        for i, p in enumerate(slots):
            if p:
                st.markdown(f"<div class='status-card'>👤 {p['name']} (機台{i+1})</div>", unsafe_allow_html=True)
            else:
                st.write(f"機台{i+1}: 🟢 空閒")

if st.session_state.waiting_queue or any(p for slots in st.session_state.equipment_status.values() for p in slots):
    time.sleep(1); st.rerun()