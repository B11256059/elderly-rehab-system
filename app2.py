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
    .waiting-row { font-size: 0.9em; padding: 10px; border-bottom: 1px solid #e2e8f0; }
    .highlight-text { color: #0e7490; font-weight: bold; }
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
if "equipment_status" not in st.session_state: st.session_state.equipment_status = {"大轉輪": None, "坐推": None, "漫步機": None}
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()  
if "cooldown_patients" not in st.session_state: st.session_state.cooldown_patients = {}
if "patient_id_counter" not in st.session_state: st.session_state.patient_id_counter = 1
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {} 

# 用於在失敗、初次登記、或是漏填時暫存畫面的狀態
if "input_last_name" not in st.session_state: st.session_state.input_last_name = ""
if "input_equips" not in st.session_state: st.session_state.input_equips = []

# 控制元件內容版號（用於需要強行刷白時）
if "form_version" not in st.session_state: st.session_state.form_version = 0

# 初始化提示狀態
if "form_status" not in st.session_state: st.session_state.form_status = {"type": None, "msg": None}

TRANSIT_COOLDOWN_SECONDS = 180 # 3分鐘換場休息

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
            "original_service_time": lookup_table.get((equip, age), 5)
        })

# ==========================================
# 5. 側邊欄模擬與控制
# ==========================================
with st.sidebar:
    st.header("👥 模擬情境")
    if st.button("🚀 注入 20 位長輩數據"):
        mock_list = [
            ("王", "爺爺", 70, ["大轉輪", "坐推"]), ("陳", "奶奶", 60, ["坐推", "漫步機"]),
            ("林", "爺爺", 80, ["漫步機"]), ("張", "奶奶", 90, ["大轉輪", "漫步機"]),
            ("李", "爺爺", 60, ["大轉輪", "坐推", "漫步機"]), ("吳", "爺爺", 70, ["坐推"]),
            ("劉", "奶奶", 80, ["大轉輪"]), ("蔡", "爺爺", 90, ["漫步機"]),
            ("楊", "奶奶", 70, ["大轉輪", "坐推"]), ("黃", "爺爺", 80, ["坐推"]),
            ("曾", "奶奶", 60, ["漫步機"]), ("洪", "爺爺", 70, ["大轉輪"]),
            ("郭", "奶奶", 80, ["漫步機"]), ("馬", "爺爺", 90, ["大轉輪", "坐推"]),
            ("徐", "奶奶", 60, ["漫步機"]), ("朱", "爺爺", 70, ["坐推"]),
            ("胡", "奶奶", 80, ["大轉輪", "漫步機"]), ("何", "爺爺", 90, ["大轉輪"]),
            ("蘇", "奶奶", 60, ["漫步機"]), ("葉", "爺爺", 70, ["大轉輪"])
        ]
        for ln_m, tit_m, age_m, eqs_m in mock_list:
            p_id_m = get_or_create_patient_id(ln_m, tit_m, age_m)
            add_patient(p_id_m, ln_m, tit_m, age_m, eqs_m)
        st.session_state.form_status = {"type": None, "msg": None}
        st.rerun()
    
    if st.button("🧹 清空所有數據"):
        st.session_state.waiting_queue = []
        st.session_state.equipment_status = {"大轉輪": None, "坐推": None, "漫步機": None}
        st.session_state.cooldown_patients = {}
        st.session_state.patient_registry = {}
        st.session_state.patient_history = {}
        st.session_state.patient_id_counter = 1
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

# 長輩日常輸入面板
with st.expander("➕ 長輩報到與處方登記", expanded=True):
    with st.form(key="patient_input_form"):
        col1, col2, col3 = st.columns([1,1,1])
        with col1: 
            # 這裡改回讀取 session_state 來保留初次登記或漏填時的數值
            input_ln = st.text_input("姓氏", value=st.session_state.input_last_name, placeholder="例如：王", key=f"ln_widget_{st.session_state.form_version}")
        with col2: 
            input_tit = st.selectbox("稱謂", ["爺爺", "奶奶"], key=f"tit_widget_{st.session_state.form_version}")
        with col3: 
            input_age = st.selectbox("年齡層", [60, 70, 80, 90], format_func=lambda x:f"{x}歲", key=f"age_widget_{st.session_state.form_version}")
        
        input_equips = st.multiselect("復健處方器材 (可多選)", ["大轉輪", "坐推", "漫步機"], default=st.session_state.input_equips, key=f"eqs_widget_{st.session_state.form_version}")
        
        submit_button = st.form_submit_button(label="進入排隊等待")
        
        if submit_button:
            # 先將當前輸入的值同步到暫存中，預設會先「留著資料」
            st.session_state.input_last_name = input_ln.strip()
            st.session_state.input_equips = input_equips
            
            missing_fields = []
            if not input_ln.strip(): missing_fields.append("「姓氏」")
            if not input_equips: missing_fields.append("「復健處方器材」")
            
            if missing_fields:
                # 🔴 狀況一：漏填欄位 -> 留著目前的資料不清洗，並顯示警告
                st.session_state.form_status = {
                    "type": "warning",
                    "msg": f"⚠️ 登記失敗！請填寫漏掉的資訊：{'、'.join(missing_fields)}。"
                }
                st.rerun()
            else:
                p_id = get_or_create_patient_id(input_ln.strip(), input_tit, input_age)
                
                # 交叉查重比對邏輯
                current_waiting_equips = [p["target_equip"] for p in st.session_state.waiting_queue if p["id"] == p_id]
                current_using_equips = [eq for eq, p in st.session_state.equipment_status.items() if p and p["id"] == p_id]
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
                    # 🔴 狀況二：【核心修改】踩到重複（做過/正在做/排隊中）
                    # 清空暫存，並升級版號 -> 強制把畫面洗回初始空白狀態！
                    st.session_state.input_last_name = ""
                    st.session_state.input_equips = []
                    st.session_state.form_version += 1
                    
                    st.session_state.form_status = {
                        "type": "warning",
                        "msg": f"❌ 登記失敗！重複排隊：{ '、'.join(invalid_equips_msg) }。"
                    }
                    st.rerun()
                else:
                    # 🟢 狀況三：普通初次登記成功 -> 順利排隊，同時也要洗白表格
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

# --- HRRN 核心調度邏輯 ---
for eq, p in list(st.session_state.equipment_status.items()):
    if p:
        if (time.time() - p["start_time"]) / 60 >= p["service_time"]:
            if p["id"] not in st.session_state.patient_history:
                st.session_state.patient_history[p["id"]] = set()
            st.session_state.patient_history[p["id"]].add(eq)
            
            st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
            st.session_state.equipment_status[eq] = None

if st.session_state.waiting_queue:
    busy_ids = {p["id"] for p in st.session_state.equipment_status.values() if p}
    now = time.time()
    
    for p in st.session_state.waiting_queue:
        wait_m = (now - p["arrival_time"]) / 60
        p["hrrn_score"] = (max(wait_m, 0.001) + p["service_time"]) / p["service_time"]
    
    st.session_state.waiting_queue.sort(key=lambda x: x["hrrn_score"], reverse=True)
    
    rem_waiting = []
    for p in st.session_state.waiting_queue:
        eq = p["target_equip"]
        is_cd = p["id"] in st.session_state.cooldown_patients
        
        if st.session_state.equipment_status[eq] is None and p["id"] not in busy_ids and not is_cd:
            p["start_time"] = now
            st.session_state.equipment_status[eq] = p
            busy_ids.add(p["id"])
        else:
            rem_waiting.append(p)
    st.session_state.waiting_queue = rem_waiting

# --- 前端雙欄看板呈現 ---
st.write("---")
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("🔴 現場排隊等待區 (HRRN 演算法)")
    if not st.session_state.waiting_queue:
        st.info("目前沒有長輩在排隊等待。")
    else:
        df = pd.DataFrame(st.session_state.waiting_queue)
        df["等待時間"] = ((time.time() - df["arrival_time"]) // 1).astype(int).apply(lambda x: f"{x}秒")
        df["年齡顯示"] = df["age"].apply(lambda x: f"{x}歲") 
        
        st.dataframe(df[["id", "name", "年齡顯示", "target_equip", "service_time", "等待時間", "hrrn_score"]].rename(columns={
            "id":"長輩編號", "name":"姓名", "年齡顯示":"年齡", "target_equip":"目標器材", "service_time":"預計時長(分)", "hrrn_score":"優先權分數(HRRN)"
        }), hide_index=True, use_container_width=True)

with right_col:
    st.subheader("🟢 復健器材運作狀態區")
    for eq, p in st.session_state.equipment_status.items():
        with st.container():
            if p:
                elapsed = int(time.time() - p["start_time"])
                st.markdown(f"""
                <div class="status-card">
                    <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                    👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) ({p['id']})</span><br>
                    ⏱️ 已執行: {elapsed//60}分{elapsed%60}秒 / 處方預計: {p['service_time']}分鐘
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button(f"🐢 未完成目標(+1分)", key=f"s_{eq}"):
                    p["service_time"] += 1
                    st.rerun()
                if c2.button(f"🐇 已完成目標(結束)", key=f"f_{eq}"):
                    if p["id"] not in st.session_state.patient_history:
                        st.session_state.patient_history[p["id"]] = set()
                    st.session_state.patient_history[p["id"]].add(eq)
                    
                    st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
                    p["service_time"] = 0
                    st.rerun()
            else:
                st.markdown(f"""<div class="status-card" style="border-left: 5px solid #cbd5e1; color: #94a3b8; padding: 25px;"><b>⚙️ {eq}</b><br>🟢 空閒中</div>""", unsafe_allow_html=True)

has_active = len(st.session_state.waiting_queue) > 0 or any(p is not None for p in st.session_state.equipment_status.values()) or len(st.session_state.cooldown_patients) > 0

if has_active:
    time.sleep(1)
    st.rerun()