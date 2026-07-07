import streamlit as st
import pandas as pd
import re
import time

# ==========================================
# 1. 網頁基本設定
# ==========================================
st.set_page_config(page_title="智慧復健動態排程系統", layout="wide")
st.markdown("""
    <style>
    .status-card { background-color: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid #10b981; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 智慧復健動態排程管理系統")

# ==========================================
# 2. 復健處方大表 (保留)
# ==========================================
st.subheader("📋 復健運動處方大表")
raw_data = [
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": "50 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 70, "組數": 4, "次數": 16, "組時間": "40 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 80, "組數": 3, "次數": 13, "組時間": "35 (AI推估)", "休息時間": "80 (參考ACSM)"},
    {"器材": "坐推", "年齡": 60, "組數": 5, "次數": 12, "組時間": "36 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "坐推", "年齡": 70, "組數": 5, "次數": 11, "組時間": "33 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "漫步機", "年齡": 60, "組數": 2, "次數": "不適用", "組時間": 450, "休息時間": "60 (參考ACSM)"},
]
st.table(pd.DataFrame(raw_data))

# ==========================================
# 3. 初始化與功能
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []
if "equipment_status" not in st.session_state: 
    st.session_state.equipment_status = {
        "大轉輪_1": None, "大轉輪_2": None,
        "坐推_1": None, "坐推_2": None, "坐推_3": None,
        "漫步機_1": None
    }
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {}
if "patient_id_counter" not in st.session_state: st.session_state.patient_id_counter = 1

def get_or_create_patient_id(last_name, title, age):
    reg_key = (last_name, title, age)
    if reg_key not in st.session_state.patient_registry:
        p_id = f"#{st.session_state.patient_id_counter:03d}"
        st.session_state.patient_registry[reg_key] = p_id
        st.session_state.patient_id_counter += 1
    return st.session_state.patient_registry[reg_key]

# ==========================================
# 4. 側邊欄與登記表單 (包含驗證)
# ==========================================
with st.sidebar:
    if st.button("🚀 注入 20 位長輩數據"):
        for i in range(20):
            p_id = get_or_create_patient_id(f"長輩{i}", "爺爺", 70)
            st.session_state.waiting_queue.append({"id": p_id, "name": f"長輩{i}爺爺", "target_equip": "大轉輪"})
        st.rerun()
    if st.button("🧹 清空所有數據"):
        st.session_state.waiting_queue = []
        st.session_state.equipment_status = {k: None for k in st.session_state.equipment_status}
        st.rerun()

with st.expander("➕ 長輩報到與處方登記", expanded=True):
    with st.form("input_form"):
        c1, c2, c3 = st.columns(3)
        ln = c1.text_input("姓氏")
        tit = c2.selectbox("稱謂", ["爺爺", "奶奶"])
        age = c3.selectbox("年齡", [60, 70, 80, 90])
        eqs = st.multiselect("復健處方器材", ["大轉輪", "坐推", "漫步機"])
        if st.form_submit_button("登記"):
            if not ln: st.warning("請填寫姓氏"); st.stop()
            p_id = get_or_create_patient_id(ln, tit, age)
            for eq in eqs:
                if any(p and p["id"] == p_id and eq in p.get("target_equip", "") for p in st.session_state.equipment_status.values()):
                    st.error(f"該長輩正在使用 {eq}，不可重複排隊"); st.stop()
                if any(p["id"] == p_id and p["target_equip"] == eq for p in st.session_state.waiting_queue):
                    st.error(f"該長輩已在 {eq} 排隊序列中"); st.stop()
                st.session_state.waiting_queue.append({"id": p_id, "name": f"{ln}{tit}", "target_equip": eq})
            st.rerun()

# ==========================================
# 5. 看板與分配邏輯
# ==========================================
# 自動分配邏輯
for p in st.session_state.waiting_queue:
    for eq_key in st.session_state.equipment_status:
        if eq_key.startswith(p["target_equip"]) and st.session_state.equipment_status[eq_key] is None:
            st.session_state.equipment_status[eq_key] = p
            st.session_state.waiting_queue.remove(p)
            break

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("🔴 現場排隊等待區")
    st.dataframe(pd.DataFrame(st.session_state.waiting_queue), use_container_width=True)

with col2:
    st.subheader("🟢 復健器材運作狀態區")
    for eq, p in st.session_state.equipment_status.items():
        if p:
            st.markdown(f"""<div class="status-card"><b>⚙️ {eq}</b>: {p['name']} 使用中</div>""", unsafe_allow_html=True)
            if st.button(f"結束 {eq}", key=f"f_{eq}"):
                st.session_state.equipment_status[eq] = None
                st.rerun()
        else:
            st.markdown(f"""<div class="status-card" style="border-left: 5px solid #cbd5e1; color: #94a3b8;"><b>⚙️ {eq}</b>: 空閒</div>""", unsafe_allow_html=True)

time.sleep(1); st.rerun()