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
        border-left: 5px solid #eab308; /* 暫停時變成黃色 */
        background-color: #fefce8;
    }
    .waiting-row { font-size: 0.9em; padding: 10px; border-bottom: 1px solid #e2e8f0; }
    .highlight-text { color: #0e7490; font-weight: bold; }
    .warning-text { color: #b45309; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 智慧復健動態排程管理系統")

# ==========================================
# 2. 原始復健運動處方大表（整合格式化邏輯）
# ==========================================
st.subheader("📋 復健運動處方大表")

raw_data = [
    # 器材一: 大轉輪
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": "50 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 70, "組數": 4, "次數": 16, "組時間": "40 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 80, "組數": 3, "次數": 13, "組時間": "35 (AI推估)", "休息時間": "80 (參考ACSM)"},
    {"器材": "大轉輪", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "90 (參考ACSM)"},
    
    # 器材二: 坐推
    {"器材": "坐推", "年齡": 60, "組數": 5, "次數": 12, "組時間": "36 (AI推估)", "休息時間": "60 (參考ACSM)"},
    {"器材": "坐推", "年齡": 70, "組數": 5, "次數": 11, "組時間": "33 (AI推估)", "休息時間": "70 (參考ACSM)"},
    {"器材": "坐推", "年齡": 80, "組數": 4, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "80 (參考ACSM)"},
    {"器材": "坐推", "年齡": 90, "組數": 3, "次數": 10, "組時間": "30 (AI推估)", "休息時間": "90 (參考ACSM)"},
    
    # 器材三: 漫步機
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
    
    if sets > 1:
        total_seconds = (set_time * sets) + (rest_time * (sets - 1))
    else:
        total_seconds = set_time * sets
        
    total_minutes = round(total_seconds / 60)
    display_total = str(total_minutes) if total_seconds > 0 else ""
    lookup_table[(item["器材"], item["年齡"])] = total_minutes if total_minutes > 0 else 5

    matrix_rows.append({
        "器材名稱": item["器材"],
        "年齡層": f"{item['年齡']} 歲",
        "次數": format_unit(item["次數"], "次"),
        "組數": format_unit(item["組數"], "組"),
        "組時間": format_unit(item["組時間"], "秒"),
        "休息時間": format_unit(item["休息時間"], "秒"),
        "總時間": format_unit(display_total, "分")
    })

df_prescription = pd.DataFrame(matrix_rows)
st.table(df_prescription)

# ==========================================
# 3. 系統狀態初始化
# ==========================================
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []  
if "total_mock_count" not in st.session_state: st.session_state.total_mock_count = 0
if "equipment_status" not in st.session_state: 
    st.session_state.equipment_status = {
        "大轉輪_1": None, 
        "坐推_1": None, "坐推_2": None, "坐推_3": None, 
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

TRANSIT_COOLDOWN_SECONDS = 180 # 3分鐘換場休息
MID_PAUSE_SECONDS = 60         # 中斷休息時間：1分鐘 (60秒)

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
            "original_service_time": lookup_table.get((equip, age), 5),
            "is_paused": False,        
            "pause_start_time": 0,      
            "total_paused_duration": 0  
        })

# ==========================================
# 5. 側邊欄模擬與控制
# ==========================================
with st.sidebar:
    st.header("👥 模擬情境")
    st.write(f"當前已模擬人數: {st.session_state.total_mock_count} / 20")
    
    if st.button("🚀 分批注入 (3-5人)"):
        if st.session_state.total_mock_count < 20:
            last_names = ["王", "陳", "林", "張", "李", "吳", "劉", "蔡", "楊", "黃", "曾", "洪", "郭", "馬", "徐", "朱", "胡", "何", "蘇", "葉"]
            equips_base = ["大轉輪", "坐推", "漫步機"]
            
            # 計算剩餘可加入名額
            remaining = 20 - st.session_state.total_mock_count
            batch_size = min(random.randint(3, 5), remaining)
            
            for _ in range(batch_size):
                ln = random.choice(last_names)
                tit = random.choice(["爺爺", "奶奶"])
                age = random.choice([60, 70, 80, 90])
                eqs = random.sample(equips_base, random.randint(1, 3))
                
                p_id = get_or_create_patient_id(ln, tit, age)
                add_patient(p_id, ln, tit, age, eqs)
                st.session_state.total_mock_count += 1
            
            st.rerun()
        else:
            st.warning("已達模擬上限 20 人！")
    
    if st.button("🧹 清空所有數據"):
        st.session_state.waiting_queue = []
        st.session_state.equipment_status = {eq: None for eq in st.session_state.equipment_status.keys()}
        st.session_state.cooldown_patients = {}
        st.session_state.patient_registry = {}
        st.session_state.patient_history = {}
        st.session_state.patient_id_counter = 1
        st.session_state.total_mock_count = 0 
        st.session_state.start_system_timestamp = time.time()
        st.session_state.form_status = {"type": None, "msg": None}
        st.session_state.input_last_name = ""
        st.session_state.input_equips = []
        st.session_state.form_version += 1
        st.rerun()

# ==========================================
# 6. 主要看板內容區
# ==========================================
st.write("---")
m1, m2, m3 = st.columns(3)

current_total_seconds = int(time.time() - st.session_state.start_system_timestamp)
system_time_text = f"{current_total_seconds // 3600} 時 {(current_total_seconds % 3600) // 60} 分 {current_total_seconds % 60} 秒"

m1.metric("營運總時長", system_time_text)
m2.metric("待辦處方數", f"{len(st.session_state.waiting_queue)} 項")

now_time = time.time()
st.session_state.cooldown_patients = {k: v for k, v in st.session_state.cooldown_patients.items() if now_time < v}
m3.metric("換場休息中(3分/人)", f"{len(st.session_state.cooldown_patients)} 人")

with st.expander("➕ 長輩報到與處方登記", expanded=True):
    with st.form(key="patient_input_form"):
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            input_ln = st.text_input("姓氏", value=st.session_state.input_last_name, placeholder="例如：王", key=f"ln_widget_{st.session_state.form_version}")
        with col2:
            input_tit = st.selectbox("稱謂", ["爺爺", "奶奶"], key=f"tit_widget_{st.session_state.form_version}")
        with col3:
            input_age = st.selectbox("年齡層", [60, 70, 80, 90], format_func=lambda x:f"{x}歲", key=f"age_widget_{st.session_state.form_version}")
        
        input_equips = st.multiselect("復健處方器材 (可多選)", ["大轉輪", "坐推", "漫步機"], default=st.session_state.input_equips, key=f"eqs_widget_{st.session_state.form_version}")
        submit_button = st.form_submit_button(label="進入排隊等待")
        
        if submit_button:
            st.session_state.input_last_name = input_ln.strip()
            st.session_state.input_equips = input_equips
            
            missing_fields = []
            if not input_ln.strip(): missing_fields.append("「姓氏」")
            if not input_equips: missing_fields.append("「復健處方器材」")
            
            if missing_fields:
                st.session_state.form_status = {
                    "type": "warning",
                    "msg": f"⚠️ 登記失敗！請填寫漏掉的資訊：{'、'.join(missing_fields)}。"
                }
                st.rerun()
            else:
                p_id = get_or_create_patient_id(input_ln.strip(), input_tit, input_age)
                current_waiting_equips = [p["target_equip"] for p in st.session_state.waiting_queue if p["id"] == p_id]
                current_using_equips = [eq.split('_')[0] for eq, p in st.session_state.equipment_status.items() if p and p["id"] == p_id]
                past_done_equips = st.session_state.patient_history.get(p_id, set())
                
                invalid_equips_msg = []
                valid_to_add = []
                
                for eq in input_equips:
                    if eq in current_using_equips:
                        invalid_equips_msg.append(f"「{eq}」正由該長輩使用中")
                    elif eq in current_waiting_equips:
                        invalid_equips_msg.append(f"「{eq}」已在排隊序列中")
                    elif eq in past_done_equips:
                        invalid_equips_msg.append(f"「{eq}」先前已成功完成復健")
                    else:
                        valid_to_add.append(eq)
                
                if invalid_equips_msg:
                    st.session_state.input_last_name = ""
                    st.session_state.input_equips = []
                    st.session_state.form_version += 1
                    st.session_state.form_status = {
                        "type": "warning",
                        "msg": f"❌ 登記失敗！重複排隊：{ '、'.join(invalid_equips_msg) }。"
                    }
                    st.rerun()
                else:
                    add_patient(p_id, input_ln.strip(), input_tit, input_age, valid_to_add)
                    st.session_state.input_last_name = ""
                    st.session_state.input_equips = []
                    st.session_state.form_version += 1
                    st.session_state.form_status = {
                        "type": "success",
                        "msg": f"⭕ 登記成功，已進入排隊！"
                    }
                    st.rerun()
        
        if st.session_state.form_status["type"] == "warning":
            st.warning(st.session_state.form_status["msg"])
        elif st.session_state.form_status["type"] == "success":
            st.success(st.session_state.form_status["msg"])

# --- HRRN 核心調度與時間維護邏輯 ---
now = time.time()
need_trigger_rerun = False 

for eq, p in list(st.session_state.equipment_status.items()):
    if p:
        if p.get("is_paused", False):
            paused_time = now - p["pause_start_time"]
            if paused_time >= MID_PAUSE_SECONDS:
                p["total_paused_duration"] += MID_PAUSE_SECONDS
                p["is_paused"] = False
                p["pause_start_time"] = 0
            else:
                continue

        active_seconds = now - p["start_time"] - p.get("total_paused_duration", 0)
        if active_seconds / 60 >= p["service_time"]:
            if p["id"] not in st.session_state.patient_history:
                st.session_state.patient_history[p["id"]] = set()
            st.session_state.patient_history[p["id"]].add(eq.split('_')[0])
            st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
            st.session_state.equipment_status[eq] = None
            need_trigger_rerun = True

if st.session_state.waiting_queue:
    busy_ids = {p["id"] for p in st.session_state.equipment_status.values() if p}
    now = time.time()
    
    for p in st.session_state.waiting_queue:
        wait_m = (now - p["arrival_time"]) / 60
        p["hrrn_score"] = (max(wait_m, 0.001) + p["service_time"]) / p["service_time"]
    
    st.session_state.waiting_queue.sort(key=lambda x: x["hrrn_score"], reverse=True)
    
    rem_waiting = []
    for p in st.session_state.waiting_queue:
        target_base = p["target_equip"]
        is_cd = p["id"] in st.session_state.cooldown_patients
        
        # 找尋對應類型的空閒機台
        available_eqs = [eq for eq, status in st.session_state.equipment_status.items() 
                        if status is None and eq.startswith(target_base)]
        
        if available_eqs and p["id"] not in busy_ids and not is_cd:
            eq = available_eqs[0]
            p["start_time"] = now
            st.session_state.equipment_status[eq] = p
            busy_ids.add(p["id"])
            need_trigger_rerun = True
        else:
            rem_waiting.append(p)
    st.session_state.waiting_queue = rem_waiting

if need_trigger_rerun:
    st.rerun()

# ==========================================
# 7. 前端雙欄看板呈現
# ==========================================
st.write("---")
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("🔴 現場排隊等待區")
    if st.session_state.waiting_queue:
        # 顯示排隊名單，包含使用者資訊
        df = pd.DataFrame(st.session_state.waiting_queue)
        # 為了呈現美觀，我們可以自定義顯示格式
        display_df = df[["id", "name", "target_equip", "hrrn_score"]]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("目前無人排隊")

with right_col:
    st.subheader("🟢 復健器材運作狀態區")
    for eq, p in st.session_state.equipment_status.items():
        current_now = time.time()
        
        # --- 1. 狀態判斷與樣式邏輯 ---
        if not p:
            # 空閒狀態 (與其他卡片完全統一的結構)
            bg_color, border_color = "#f0fdf4", "#22c55e"
            status_html = "🟢 目前空閒中，歡迎使用"
            st.markdown(f'''
                <div class="status-card" style="background-color: {bg_color}; border-left: 5px solid {border_color}; margin-bottom: 10px; padding: 15px; border-radius: 8px;">
                    <b style="font-size:1.1em;">⚙️ {eq}</b><br>{status_html}
                </div>
            ''', unsafe_allow_html=True)
        else:
            is_paused, started = p.get("is_paused", False), p.get("is_started", False)
            
            if not started:
                # 等待開始邏輯 (1分鐘變紅，90秒釋放)
                wait_time = current_now - p["arrival_time"]
                if wait_time > 90: st.session_state.equipment_status[eq] = None; st.rerun()
                
                if wait_time > 60:
                    bg_color, border_color = "#fee2e2", "#ef4444"
                    status_html = f"👤 {p['name']} ({p['age']}歲) [{p['id']}]<br><span style='color:#b91c1c; font-weight:bold;'>⏳ 逾時倒數: {int(90 - wait_time)}秒</span>"
                else:
                    bg_color, border_color = "#eff6ff", "#3b82f6"
                    status_html = f"👤 {p['name']} ({p['age']}歲) [{p['id']}]<br>▶️ 等待開始復健..."
                
                st.markdown(f'''
                    <div class="status-card" style="background-color: {bg_color}; border-left: 5px solid {border_color}; margin-bottom: 10px; padding: 15px; border-radius: 8px;">
                        <b style="font-size:1.1em;">⚙️ {eq}</b><br>{status_html}
                    </div>
                ''', unsafe_allow_html=True)
                
                if st.button("▶️ 開始復健", key=f"start_{eq}"): p["is_started"]=True; p["start_time"]=time.time(); st.rerun()
            
            elif is_paused:
                # 休息中狀態
                elapsed = int(p["pause_start_time"] - p["start_time"] - p.get("total_paused_duration", 0))
                rem_pause = max(0, int(MID_PAUSE_SECONDS - (current_now - p["pause_start_time"])))
                bg_color, border_color = "#fefce8", "#eab308"
                status_html = f"👤 {p['name']} ({p['age']}歲) [{p['id']}]<br>⏱️ 已執行: {elapsed//60}分{elapsed%60}秒 (休息倒數: {rem_pause}秒)"
                st.markdown(f'''
                    <div class="status-card" style="background-color: {bg_color}; border-left: 5px solid {border_color}; margin-bottom: 10px; padding: 15px; border-radius: 8px;">
                        <b style="font-size:1.1em;">⚙️ {eq}</b><br>{status_html}
                    </div>
                ''', unsafe_allow_html=True)
                if st.button("▶️ 跳過休息 (繼續)", key=f"res_{eq}"): p["total_paused_duration"]+=(time.time()-p["pause_start_time"]); p["is_paused"]=False; st.rerun()
            
            else:
                # 執行中狀態
                elapsed = int(current_now - p["start_time"] - p.get("total_paused_duration", 0))
                bg_color, border_color = "#ffffff", "#10b981"
                status_html = f"👤 {p['name']} ({p['age']}歲) [{p['id']}]<br>⏱️ 已執行: {elapsed//60}分{elapsed%60}秒 / 目標: {p['service_time']}分"
                st.markdown(f'''
                    <div class="status-card" style="background-color: {bg_color}; border-left: 5px solid {border_color}; margin-bottom: 10px; padding: 15px; border-radius: 8px;">
                        <b style="font-size:1.1em;">⚙️ {eq}</b><br>{status_html}
                    </div>
                ''', unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button("⏸️ 中斷休息", key=f"s_{eq}"): p["is_paused"]=True; p["pause_start_time"]=time.time(); st.rerun()
                if c2.button("🐇 已完成目標", key=f"f_{eq}"): 
                    st.session_state.patient_history.setdefault(p["id"], set()).add(eq.split('_')[0])
                    st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
                    st.session_state.equipment_status[eq] = None; st.rerun()
            else:
                st.markdown(f"""<div class="status-card" style="border-left: 5px solid #cbd5e1; color: #94a3b8; padding: 25px;"><b>⚙️ {eq}</b><br>🟢 空閒中</div>""", unsafe_allow_html=True)
has_active = len(st.session_state.waiting_queue) > 0 or any(p is not None for p in st.session_state.equipment_status.values()) or len(st.session_state.cooldown_patients) > 0

if has_active:
    time.sleep(1)
    st.rerun()