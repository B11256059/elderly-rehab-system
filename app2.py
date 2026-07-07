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
# 2. 數據定義
# ==========================================
# 定義所有機台名稱
EQUIPMENT_LIST = ["大轉輪_1", "大轉輪_2", "坐推_1", "坐推_2", "坐推_3", "漫步機_1"]
# 用於快速獲取基礎器材名稱 (去掉編號)
def get_base_equip(equip_name):
    return equip_name.split('_')[0]

raw_data = [
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": "50 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "坐推", "年齡": 60, "組數": 5, "次數": 12, "組時間": "36 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "漫步機", "年齡": 60, "組數": 2, "次數": "不適用", "組時間": 450, "休息時間": "60 (參考ACSM)"},
    # 為簡化範例，其餘年齡層省略部分，邏輯同上
]

# 輔助函數保持不變
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
    numbers = re.findall(r'\d+', str(value))
    return int(numbers[0]) if numbers else 0

# 建立查詢表
lookup_table = {}
for item in raw_data:
    lookup_table[(item["器材"], item["年齡"])] = 5 # 預設值

# ==========================================
# 3. 系統狀態初始化
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []  
if "equipment_status" not in st.session_state: 
    st.session_state.equipment_status = {eq: None for eq in EQUIPMENT_LIST}
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()  
if "cooldown_patients" not in st.session_state: st.session_state.cooldown_patients = {}
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {} # {id: set(base_equip_names)}
if "patient_id_counter" not in st.session_state: st.session_state.patient_id_counter = 1

# ==========================================
# 4. 邏輯函數
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
            "service_time": lookup_table.get((get_base_equip(equip), age), 5),
            "is_paused": False, "pause_start_time": 0, "total_paused_duration": 0
        })

# ==========================================
# 5. 側邊欄與功能區
# ==========================================
with st.sidebar:
    if st.button("🚀 注入 20 位長輩數據"):
        # 注入邏輯保持相同，但機台名稱對應新的清單
        mock_list = [("王", "爺爺", 70, ["大轉輪_1", "坐推_1"]), ("陳", "奶奶", 60, ["坐推_2", "漫步機_1"])]
        for ln_m, tit_m, age_m, eqs_m in mock_list:
            p_id = get_or_create_patient_id(ln_m, tit_m, age_m)
            add_patient(p_id, ln_m, tit_m, age_m, eqs_m)
        st.rerun()
    if st.button("🧹 清空所有數據"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 6. 主邏輯處理
# ==========================================
now = time.time()
# 更新狀態與自動釋放機台
for eq, p in list(st.session_state.equipment_status.items()):
    if p:
        if p.get("is_paused"):
            if now - p["pause_start_time"] >= 60:
                p["total_paused_duration"] += 60
                p["is_paused"] = False
        if (now - p["start_time"] - p.get("total_paused_duration", 0)) / 60 >= p["service_time"]:
            st.session_state.patient_history.setdefault(p["id"], set()).add(get_base_equip(eq))
            st.session_state.equipment_status[eq] = None

# 排隊調度
busy_ids = {p["id"] for p in st.session_state.equipment_status.values() if p}
for p in st.session_state.waiting_queue[:]:
    eq = p["target_equip"]
    if st.session_state.equipment_status[eq] is None and p["id"] not in busy_ids:
        p["start_time"] = now
        st.session_state.equipment_status[eq] = p
        busy_ids.add(p["id"])
        st.session_state.waiting_queue.remove(p)

# ==========================================
# 7. 前端畫面
# ==========================================
# (報到 Form 省略，保持原樣，只需將 multiselect 選項改為 EQUIPMENT_LIST)
# 防呆修改關鍵：
# 在 Form submit 邏輯中，檢查 if get_base_equip(eq) in st.session_state.patient_history.get(p_id, set())

st.subheader("🟢 復健器材運作狀態")
cols = st.columns(3)
for i, (eq, p) in enumerate(st.session_state.equipment_status.items()):
    with cols[i % 3]:
        if p:
            st.markdown(f"**{eq}** - 使用者: {p['name']}")
            # 顯示控制按鈕
        else:
            st.markdown(f"**{eq}** - 空閒")