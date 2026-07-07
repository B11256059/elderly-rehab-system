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
    .status-card { background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-left: 5px solid #10b981; margin-bottom: 20px; }
    .highlight-text { color: #0e7490; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 智慧復健動態排程管理系統")

# ==========================================
# 2. 處方大表邏輯
# ==========================================
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

def extract_number(value):
    val_str = str(value).strip()
    if "不適用" in val_str: return 0
    numbers = re.findall(r'\d+', val_str)
    return int(numbers[0]) if numbers else 0

lookup_table = {}
for item in raw_data:
    sets = extract_number(item["組數"])
    set_time = extract_number(item["組時間"])
    rest_time = extract_number(item["休息時間"])
    total_m = round(((set_time * sets) + (rest_time * (sets - 1))) / 60) if sets > 1 else round((set_time * sets)/60)
    lookup_table[(item["器材"], item["年齡"])] = total_m if total_m > 0 else 5

# ==========================================
# 3. 初始化狀態
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

# ==========================================
# 4. 功能函數與驗證邏輯
# ==========================================
def get_or_create_patient_id(last_name, title, age):
    reg_key = (last_name, title, age)
    if reg_key not in st.session_state.patient_registry:
        p_id = f"#{st.session_state.patient_id_counter:03d}"
        st.session_state.patient_registry[reg_key] = p_id
        st.session_state.patient_id_counter += 1
    return st.session_state.patient_registry[reg_key]

# ==========================================
# 5. 側邊欄與登記表單
# ==========================================
with st.sidebar:
    if st.button("🚀 注入 20 位數據"):
        for i in range(20):
            p_id = get_or_create_patient_id(f"長輩{i}", "爺爺", 70)
            st.session_state.waiting_queue.append({"id": p_id, "name": f"長輩{i}爺爺", "age": 70, "target_equip": "大轉輪", "service_time": 5})
        st.rerun()
    if st.button("🧹 清空所有數據"):
        st.session_state.waiting_queue = []
        st.session_state.equipment_status = {k: None for k in st.session_state.equipment_status}
        st.session_state.patient_history = {}
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
            
            # 驗證邏輯
            for eq in eqs:
                # 檢查是否使用中
                if any(p and p["id"] == p_id and eq in p["target_equip"] for p in st.session_state.equipment_status.values()):
                    st.error(f"該長輩正在使用 {eq}，不可重複排隊"); st.stop()
                # 檢查是否已在隊列
                if any(p["id"] == p_id and p["target_equip"] == eq for p in st.session_state.waiting_queue):
                    st.error(f"該長輩已在 {eq} 排隊序列中"); st.stop()
                # 檢查是否已完成
                if eq in st.session_state.patient_history.get(p_id, set()):
                    st.error(f"該長輩已完成 {eq} 復健"); st.stop()
                
                st.session_state.waiting_queue.append({
                    "id": p_id, "name": f"{ln}{tit}", "age": age,
                    "target_equip": eq, "arrival_time": time.time(),
                    "service_time": lookup_table.get((eq, age), 5)
                })
            st.rerun()

# ==========================================
# 6. 調度邏輯 (自動分配)
# ==========================================
for p in st.session_state.waiting_queue:
    # 尋找目標類別的空閒機台
    for eq_key in st.session_state.equipment_status:
        if eq_key.startswith(p["target_equip"]) and st.session_state.equipment_status[eq_key] is None:
            st.session_state.equipment_status[eq_key] = p
            st.session_state.waiting_queue.remove(p)
            break

# ==========================================
# 7. 看板
# ==========================================
col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("🔴 現場排隊等待區")
    if st.session_state.waiting_queue:
        st.dataframe(pd.DataFrame(st.session_state.waiting_queue)[["id", "name", "target_equip"]], use_container_width=True)

with col2:
    st.subheader("🟢 復健器材運作狀態區")
    for eq, p in st.session_state.equipment_status.items():
        if p:
            st.markdown(f"""<div class="status-card"><b>⚙️ {eq}</b><br>👤 {p['name']} ({p['id']}) 正在使用</div>""", unsafe_allow_html=True)
            if st.button(f"結束 {eq}", key=f"finish_{eq}"):
                st.session_state.patient_history.setdefault(p["id"], set()).add(p["target_equip"])
                st.session_state.equipment_status[eq] = None
                st.rerun()
        else:
            st.markdown(f"""<div class="status-card" style="border-left: 5px solid #cbd5e1; color: #94a3b8;"><b>⚙️ {eq}</b><br>🟢 空閒中</div>""", unsafe_allow_html=True)

time.sleep(1); st.rerun()