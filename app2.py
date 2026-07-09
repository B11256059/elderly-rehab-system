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
# 2. 基礎資料設定
# ==========================================
EQUIPMENT_LIST = ["大轉輪", "坐推", "漫步機"]
raw_data = [
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": "50", "休息時間": "60"},
    {"器材": "大轉輪", "年齡": 70, "組數": 4, "次數": 16, "組時間": "40", "休息時間": "70"},
    {"器材": "大轉輪", "年齡": 80, "組數": 3, "次數": 13, "組時間": "35", "休息時間": "80"},
    {"器材": "大轉輪", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30", "休息時間": "90"},
    {"器材": "坐推", "年齡": 60, "組數": 5, "次數": 12, "組時間": "36", "休息時間": "60"},
    {"器材": "坐推", "年齡": 70, "組數": 5, "次數": 11, "組時間": "33", "休息時間": "70"},
    {"器材": "坐推", "年齡": 80, "組數": 4, "次數": 10, "組時間": "30", "休息時間": "80"},
    {"器材": "坐推", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30", "休息時間": "90"},
    {"器材": "漫步機", "年齡": 60, "組數": 2, "次數": "0", "組時間": 450, "休息時間": "60"},
    {"器材": "漫步機", "年齡": 70, "組數": 2, "次數": "0", "組時間": 390, "休息時間": "70"},
    {"器材": "漫步機", "年齡": 80, "組數": 2, "次數": "0", "組時間": 330, "休息時間": "80"},
    {"器材": "漫步機", "年齡": 90, "組數": 2, "次數": "0", "組時間": 300, "休息時間": "90"},
]

lookup_table = {}
for item in raw_data:
    lookup_table[(item["器材"], item["年齡"])] = round((int(item["組時間"]) * int(item["組數"]) + int(item["休息時間"]) * (int(item["組數"]) - 1)) / 60)

# ==========================================
# 3. 系統狀態初始化
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []  
if "equipment_status" not in st.session_state: 
    st.session_state.equipment_status = {"大轉輪_1": None, "坐推_1": None, "坐推_2": None, "坐推_3": None, "漫步機_1": None, "漫步機_2": None}
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()  
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {}
if "total_mocked_count" not in st.session_state: st.session_state.total_mocked_count = 0
if "auto_mock_active" not in st.session_state: st.session_state.auto_mock_active = False
if "next_mock_time" not in st.session_state: st.session_state.next_mock_time = time.time()

# ==========================================
# 4. 模擬邏輯與功能函數
# ==========================================
def add_patient(last_name, title, age, selected_equips):
    p_key = (last_name, title, age)
    if p_key not in st.session_state.patient_registry:
        p_id = f"#{len(st.session_state.patient_registry)+1:03d}"
        st.session_state.patient_registry[p_key] = p_id
    p_id = st.session_state.patient_registry[p_key]
    
    for equip in selected_equips:
        st.session_state.waiting_queue.append({
            "id": p_id, "name": f"{last_name}{title}", "age": age,
            "target_equip": equip, "arrival_time": time.time(),
            "service_time": lookup_table.get((equip, age), 5),
            "is_paused": False, "pause_start_time": 0, "total_paused_duration": 0
        })

# ==========================================
# 5. 側邊欄與自動模擬控制
# ==========================================
with st.sidebar:
    st.header("⚙️ 控制面板")
    if st.button("▶️ 開始自動模擬 (共20人)"):
        st.session_state.auto_mock_active = True
        st.session_state.total_mocked_count = 0
        st.session_state.next_mock_time = time.time()
        st.rerun()
    
    if st.button("🧹 清空系統"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 自動模擬執行區 ---
if st.session_state.auto_mock_active and st.session_state.total_mocked_count < 20:
    if time.time() >= st.session_state.next_mock_time:
        # 決定這批來幾人 (1-3人)
        batch_size = random.randint(1, 3)
        for _ in range(batch_size):
            if st.session_state.total_mocked_count < 20:
                ln = random.choice(["王", "陳", "林", "張", "李", "吳", "劉", "蔡"])
                tit = random.choice(["爺爺", "奶奶"])
                age = random.choice([60, 70, 80, 90])
                # 隨機選擇 1-3 個不重複器材
                eqs = random.sample(EQUIPMENT_LIST, k=random.randint(1, 3))
                add_patient(ln, tit, age, eqs)
                st.session_state.total_mocked_count += 1
        
        st.session_state.next_mock_time = time.time() + random.uniform(5, 15)
        st.rerun()

# ==========================================
# 6. 主要內容呈現 (邏輯同前，略過細節以精簡)
# ==========================================
# ... [此處放入您原有的 HRRN 排程與前端顯示邏輯] ...
# 為了長度限制，請將您原先程式碼中從 # 6. 主要看板內容區 到結尾的程式碼複製補上即可