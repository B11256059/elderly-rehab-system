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
    .waiting-row { font-size: 0.9em; padding: 10px; border-bottom: 1px solid #e2e8f0; }
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
    {"器材": "大轉輪", "年齡": 60, "組數": 5, "次數": 20, "組時間": 50, "休息時間": 60},
    {"器材": "大轉輪", "年齡": 70, "組數": 4, "次數": 16, "組時間": 40, "休息時間": 70},
    {"器材": "大轉輪", "年齡": 80, "組數": 3, "次數": 13, "組時間": 35, "休息時間": 80},
    {"器材": "大轉輪", "年齡": 90, "組數": 3, "次數": 10, "組時間": 30, "休息時間": 90},
    
    {"器材": "坐推", "年齡": 60, "組數": 5, "次數": 12, "組時間": 36, "休息時間": 60},
    {"器材": "坐推", "年齡": 70, "組數": 5, "次數": 11, "組時間": 33, "休息時間": 70},
    {"器材": "坐推", "年齡": 80, "組數": 4, "次數": 10, "組時間": 30, "休息時間": 80},
    {"器材": "坐推", "年齡": 90, "組數": 3, "次數": 10, "組時間": 30, "休息時間": 90},
    
    {"器材": "漫步機", "年齡": 60, "組數": 2, "次數": "不適用", "組時間": 225, "休息時間": 60},
    {"器材": "漫步機", "年齡": 70, "組數": 2, "次數": "不適用", "組時間": 195, "休息時間": 70},
    {"器材": "漫步機", "年齡": 80, "組數": 2, "次數": "不適用", "組時間": 165, "休息時間": 80},
    {"器材": "漫步機", "年齡": 90, "組數": 2, "次數": "不適用", "組時間": 150, "休息時間": 90},

    {"器材": "肩關節康復器", "年齡": 60, "組數": 5, "次數": 20, "組時間": 45, "休息時間": 60},
    {"器材": "肩關節康復器", "年齡": 70, "組數": 4, "次數": 16, "組時間": 38, "休息時間": 70},
    {"器材": "肩關節康復器", "年齡": 80, "組數": 3, "次數": 13, "組時間": 32, "休息時間": 80},
    {"器材": "肩關節康復器", "年齡": 90, "組數": 3, "次數": 10, "組時間": 28, "休息時間": 90},

    {"器材": "復健助行車", "年齡": 60, "組數": 2, "次數": "不適用", "組時間": 150, "休息時間": 60},
    {"器材": "復健助行車", "年齡": 70, "組數": 4, "次數": "不適用", "組時間": 75, "休息時間": 70},
    {"器材": "復健助行車", "年齡": 80, "組數": 6, "次數": "不適用", "組時間": 50, "休息時間": 80},
    {"器材": "復健助行車", "年齡": 90, "組數": 8, "次數": "不適用", "組時間": 37, "休息時間": 90},
]

def format_unit(value, unit):
    val_str = str(value).strip()
    if val_str == "" or val_str == "0": return f"- {unit}"
    if unit in val_str or "不適用" in val_str: return val_str
    return f"{val_str} {unit}"

matrix_rows = []
lookup_table = {}
prescription_details = {}

for item in raw_data:
    sets = int(item["組數"])
    set_time = int(item["組時間"])
    rest_time = int(item["休息時間"])
    
    if sets > 1:
        total_seconds = (set_time * sets) + (rest_time * (sets - 1))
    else:
        total_seconds = set_time * sets
        
    total_minutes = max(1, round(total_seconds / 60))
    
    lookup_table[(item["器材"], item["年齡"])] = total_minutes
    prescription_details[(item["器材"], item["年齡"])] = {
        "sets": sets,
        "set_time": set_time,
        "rest_time": rest_time
    }

    matrix_rows.append({
        "器材名稱": item["器材"],
        "年齡層": f"{item['年齡']} 歲",
        "次數": format_unit(item["次數"], "次"),
        "組數": format_unit(item["組數"], "組"),
        "組時間": format_unit(item["組時間"], "秒"),
        "休息時間": format_unit(item["休息時間"], "秒"),
        "總時間": f"{total_minutes} 分"
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
        "漫步機_1": None, "漫步機_2": None,
        "肩關節康復器_1": None,
        "復健助行車_1": None, "復健助行車_2": None, "復健助行車_3": None
    }
if "start_system_timestamp" not in st.session_state: st.session_state.start_system_timestamp = time.time()  
if "cooldown_patients" not in st.session_state: st.session_state.cooldown_patients = {}
if "patient_id_counter" not in st.session_state: st.session_state.patient_id_counter = 1
if "patient_registry" not in st.session_state: st.session_state.patient_registry = {}
if "patient_history" not in st.session_state: st.session_state.patient_history = {}
if "patient_groups" not in st.session_state: st.session_state.patient_groups = {} 

if "input_last_name" not in st.session_state: st.session_state.input_last_name = ""
if "input_companion_id" not in st.session_state: st.session_state.input_companion_id = "" 
if "input_equips" not in st.session_state: st.session_state.input_equips = []
if "form_version" not in st.session_state: st.session_state.form_version = 0
if "form_status" not in st.session_state: st.session_state.form_status = {"type": None, "msg": None}

TRANSIT_COOLDOWN_SECONDS = 180 
MID_PAUSE_SECONDS = 60        

# ==========================================
# 4. 功能函數
# ==========================================
def get_or_create_patient_id(last_name, title, age):
    reg_key = (last_name, title, age)
    if reg_key not in st.session_state.patient_registry:
        p_id = st.session_state.patient_id_counter
        st.session_state.patient_registry[reg_key] = p_id
        st.session_state.patient_id_counter += 1
    else:
        p_id = st.session_state.patient_registry[reg_key]
    return p_id

def add_patient(p_id, last_name, title, age, selected_equips, group_id=None):
    for equip in selected_equips:
        pres_info = prescription_details.get((equip, age), {"sets": 3, "set_time": 30, "rest_time": 60})
        st.session_state.waiting_queue.append({
            "id": p_id, "name": f"{last_name}{title}", "age": age,
            "target_equip": equip, "arrival_time": time.time(),
            "service_time": lookup_table.get((equip, age), 5),
            "prescription_detail": pres_info,
            "is_paused": False,      
            "pause_start_time": 0,      
            "group_id": group_id       
        })

# ==========================================
# 5. 側邊欄模擬與控制
# ==========================================
with st.sidebar:
    st.header("👥 模擬情境")
    st.write(f"當前已模擬人數: {st.session_state.total_mock_count} / 20")
    
    if st.button("🚀 分批注入"):
        if st.session_state.total_mock_count < 20:
            last_names = ["王", "陳", "林", "張", "李", "吳", "劉", "蔡", "楊", "黃", "曾", "洪", "郭", "馬", "徐"]
            ages_base = [60, 70, 80, 90]
            titles_base = ["爺爺", "奶奶"]
            equips_base = ["大轉輪", "坐推", "漫步機", "肩關節康復器", "復健助行車"]
            
            remaining = 20 - st.session_state.total_mock_count
            inject_mode = random.choices([1, 2, 3], weights=[50, 30, 20], k=1)[0]
            batch_size = min(inject_mode, remaining)
            
            if batch_size == 1:
                ln = random.choice(last_names); tit = random.choice(titles_base); age = random.choice(ages_base); eqs = random.sample(equips_base, random.randint(1, 3))
                p_id = get_or_create_patient_id(ln, tit, age)
                add_patient(p_id, ln, tit, age, eqs, group_id=None)
                st.session_state.total_mock_count += 1
            
            elif batch_size == 2:
                ln1 = random.choice(last_names); tit1 = random.choice(titles_base); age1 = random.choice(ages_base); eqs1 = random.sample(equips_base, random.randint(1, 3))
                p1_id = get_or_create_patient_id(ln1, tit1, age1)
                add_patient(p1_id, ln1, tit1, age1, eqs1, group_id=None)
                
                ln2 = random.choice(last_names); tit2 = random.choice(titles_base); age2 = random.choice(ages_base); eqs2 = random.sample(equips_base, random.randint(1, 3))
                p2_id = get_or_create_patient_id(ln2, tit2, age2)
                add_patient(p2_id, ln2, tit2, age2, eqs2, group_id=p1_id)
                
                st.session_state.patient_groups[p1_id] = {p1_id, p2_id}
                st.session_state.patient_groups[p2_id] = {p1_id, p2_id}
                st.session_state.total_mock_count += 2
                
            elif batch_size >= 3:
                ln1 = random.choice(last_names); tit1 = random.choice(titles_base); age1 = random.choice(ages_base); eqs1 = random.sample(equips_base, random.randint(1, 3))
                p1_id = get_or_create_patient_id(ln1, tit1, age1)
                add_patient(p1_id, ln1, tit1, age1, eqs1, group_id=None)
                
                ln2 = random.choice(last_names); tit2 = random.choice(titles_base); age2 = random.choice(ages_base); eqs2 = random.sample(equips_base, random.randint(1, 3))
                p2_id = get_or_create_patient_id(ln2, tit2, age2)
                add_patient(p2_id, ln2, tit2, age2, eqs2, group_id=p1_id)
                
                ln3 = random.choice(last_names); tit3 = random.choice(titles_base); age3 = random.choice(ages_base); eqs3 = random.sample(equips_base, random.randint(1, 3))
                p3_id = get_or_create_patient_id(ln3, tit3, age3)
                add_patient(p3_id, ln3, tit3, age3, eqs3, group_id=p1_id)
                
                group_set = {p1_id, p2_id, p3_id}
                st.session_state.patient_groups[p1_id] = group_set
                st.session_state.patient_groups[p2_id] = group_set
                st.session_state.patient_groups[p3_id] = group_set
                st.session_state.total_mock_count += 3
            
            st.rerun()
        else:
            st.warning("已達模擬上限 20 人！")
    
    if st.button("🧹 清空所有數據"):
        st.session_state.waiting_queue = []
        st.session_state.equipment_status = {eq: None for eq in st.session_state.equipment_status.keys()}
        st.session_state.cooldown_patients = {}
        st.session_state.patient_registry = {}
        st.session_state.patient_history = {}
        st.session_state.patient_groups = {}
        st.session_state.patient_id_counter = 1
        st.session_state.total_mock_count = 0 
        st.session_state.start_system_timestamp = time.time()
        st.session_state.form_status = {"type": None, "msg": None}
        st.session_state.input_last_name = ""
        st.session_state.input_companion_id = ""
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
    next_preview_id = st.session_state.patient_id_counter
    st.info(f"💡 提示：下一位報到的長輩系統編號為 **#{next_preview_id}**。")

    with st.form(key="patient_input_form"):
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            input_ln = st.text_input("姓氏", value=st.session_state.input_last_name, placeholder="例如：王", key=f"ln_widget_{st.session_state.form_version}")
        with col2:
            input_tit = st.selectbox("稱謂", ["爺爺", "奶奶"], key=f"tit_widget_{st.session_state.form_version}")
        with col3:
            input_age = st.selectbox("年齡層", [60, 70, 80, 90], format_func=lambda x:f"{x}歲", key=f"age_widget_{st.session_state.form_version}")
        with col4:
            input_comp_id = st.text_input("同行者編號 (選填)", value=st.session_state.input_companion_id, placeholder="例如：1", key=f"comp_widget_{st.session_state.form_version}")
        
        input_equips = st.multiselect("復健處方器材 (可多選 1~5 項)", ["大轉輪", "坐推", "漫步機", "肩關節康復器", "復健助行車"], default=st.session_state.input_equips, key=f"eqs_widget_{st.session_state.form_version}")
        submit_button = st.form_submit_button(label="進入排隊等待")
        
        if submit_button:
            st.session_state.input_last_name = input_ln.strip()
            st.session_state.input_companion_id = input_comp_id.strip()
            st.session_state.input_equips = input_equips
            
            if not input_ln.strip() or not input_equips:
                st.session_state.form_status = {"type": "warning", "msg": "⚠️ 登記失敗！請填寫姓氏與選擇至少一項復健器材。"}
                st.rerun()
            else:
                p_id = get_or_create_patient_id(input_ln.strip(), input_tit, input_age)
                final_group_id = None
                if input_comp_id.strip():
                    try:
                        target_comp_id = int(input_comp_id.strip())
                        if target_comp_id in st.session_state.patient_registry.values():
                            final_group_id = target_comp_id 
                            if target_comp_id not in st.session_state.patient_groups:
                                st.session_state.patient_groups[target_comp_id] = {target_comp_id}
                            st.session_state.patient_groups[target_comp_id].add(p_id)
                            st.session_state.patient_groups[p_id] = st.session_state.patient_groups[target_comp_id]
                        else:
                            st.session_state.form_status = {"type": "warning", "msg": f"⚠️ 找不到編號「{target_comp_id}」的長輩！"}
                            st.rerun()
                    except ValueError:
                        st.session_state.form_status = {"type": "warning", "msg": "⚠️ 同行編號請輸入純數字！"}
                        st.rerun()

                add_patient(p_id, input_ln.strip(), input_tit, input_age, input_equips, group_id=final_group_id)
                st.session_state.input_last_name = ""
                st.session_state.input_companion_id = ""
                st.session_state.input_equips = []
                st.session_state.form_version += 1
                st.session_state.form_status = {"type": "success", "msg": f"⭕ 登記成功！編號 #{p_id}"}
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
            if now - p["pause_start_time"] >= MID_PAUSE_SECONDS:
                p["is_paused"] = False
                p["pause_start_time"] = 0
                need_trigger_rerun = True
            else:
                need_trigger_rerun = True

        # 如果正在組間休息
        if p.get("is_in_rest_period", False):
            rest_elapsed = now - p["rest_start_time"]
            pres = p["prescription_detail"]
            if rest_elapsed >= pres["rest_time"]:
                p["is_in_rest_period"] = False
                p["current_set"] += 1
                p["start_time"] = time.time()
                p["prompted_set"] = p["current_set"] - 1
                need_trigger_rerun = True
            else:
                need_trigger_rerun = True  
            continue

        # 如果正在彈出「是否完成」的視窗，暫停自動檢查，等待使用者按按鈕
        if p.get("show_target_reached_modal", False):
            continue

        # 淨執行時間持續運作，不因中斷休息而停下
        net_active_seconds = now - p["start_time"]
        
        pres = p["prescription_detail"]
        sets = pres["sets"]
        set_time = pres["set_time"]
        
        if "current_set" not in p: p["current_set"] = 1
        if "prompted_set" not in p: p["prompted_set"] = 0

        # 當時間達到設定值，且該組尚未被彈窗詢問過
        if net_active_seconds >= set_time and p["current_set"] > p["prompted_set"]:
            p["show_target_reached_modal"] = True
            need_trigger_rerun = True
        else:
            need_trigger_rerun = True

if st.session_state.waiting_queue:
    busy_ids = {p["id"] for p in st.session_state.equipment_status.values() if p}
    now = time.time()
    
    for p in st.session_state.waiting_queue:
        if p["id"] in busy_ids:
            p["arrival_time"] = now - (p.get("frozen_wait_seconds", 0))
            p["hrrn_score"] = 0.0
            continue
            
        wait_seconds = now - p["arrival_time"]
        p["frozen_wait_seconds"] = wait_seconds
        wait_m = wait_seconds / 60
        p["hrrn_score"] = (max(wait_m, 0.001) + p["service_time"]) / p["service_time"]
    
    st.session_state.waiting_queue.sort(key=lambda x: x["hrrn_score"], reverse=True)
    
    rem_waiting = []
    for p in st.session_state.waiting_queue:
        target_base = p["target_equip"]
        is_cd = p["id"] in st.session_state.cooldown_patients
        available_eqs = [eq for eq, status in st.session_state.equipment_status.items() if status is None and eq.startswith(target_base)]
        
        assigned = False
        if available_eqs and p["id"] not in busy_ids and not is_cd:
            group_id = p.get("group_id")
            if group_id:
                companions = [comp for comp in st.session_state.waiting_queue 
                            if (comp.get("group_id") == group_id or comp["id"] == group_id) 
                            and comp["target_equip"] == target_base 
                            and comp["id"] not in busy_ids 
                            and comp["id"] not in st.session_state.cooldown_patients]
                
                if len(available_eqs) >= len(companions):
                    for comp in companions:
                        comp_avail_eqs = [eq for eq, status in st.session_state.equipment_status.items() if status is None and eq.startswith(target_base)]
                        if comp_avail_eqs:
                            eq_to_assign = comp_avail_eqs[0]
                            comp["start_time"] = time.time()
                            comp["show_target_reached_modal"] = False
                            comp["current_set"] = 1
                            comp["prompted_set"] = 0
                            comp["is_in_rest_period"] = False
                            st.session_state.equipment_status[eq_to_assign] = comp
                            busy_ids.add(comp["id"])
                    assigned = True
                    need_trigger_rerun = True
            
            if not assigned:
                eq = available_eqs[0]
                p["start_time"] = time.time()
                p["show_target_reached_modal"] = False
                p["current_set"] = 1
                p["prompted_set"] = 0
                p["is_in_rest_period"] = False
                st.session_state.equipment_status[eq] = p
                busy_ids.add(p["id"])
                need_trigger_rerun = True
        else:
            rem_waiting.append(p)
            
    st.session_state.waiting_queue = [p for p in rem_waiting if p["id"] not in busy_ids]
    need_trigger_rerun = True

# ==========================================
# 7. 前端雙欄看板呈現
# ==========================================
st.write("---")
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("🔴 現場排隊等待區")
    if st.session_state.waiting_queue:
        now = time.time()
        display_data = []
        for p in st.session_state.waiting_queue:
            wait_seconds = int(now - p["arrival_time"])
            id_str = f"#{p['id']:03d}"
            
            p_id = p["id"]
            if p_id in st.session_state.patient_groups:
                group_members = st.session_state.patient_groups[p_id]
                other_members = [f"#{m:03d}" for m in group_members if m != p_id]
                group_str = ", ".join(other_members) if other_members else ""
            else:
                group_str = f"#{p['group_id']:03d}" if p.get("group_id") else ""
            
            display_data.append({
                "長輩編號": id_str,
                "姓名": p["name"],
                "年齡": f"{p['age']}歲",
                "目標器材": p["target_equip"],
                "同行編號": group_str,
                "等待時間": f"{wait_seconds}秒",
                "優先權分數(HRRN)": round(p.get("hrrn_score", 0), 4)
            })
        st.table(pd.DataFrame(display_data)) 
    else:
        st.info("目前無人排隊")

with right_col:
    st.subheader("🟢 復健器材運作狀態區")
    for eq, p in st.session_state.equipment_status.items():
        with st.container():
            if p:
                current_now = time.time()
                is_currently_paused = p.get("is_paused", False)
                is_in_rest = p.get("is_in_rest_period", False)
                show_modal = p.get("show_target_reached_modal", False)
                
                if "current_set" not in p: p["current_set"] = 1
                if "prompted_set" not in p: p["prompted_set"] = 0
                
                if not p.get("is_started", False):
                    if "assigned_time" not in p: p["assigned_time"] = time.time()
                    wait_time = current_now - p.get("assigned_time", current_now)
                    
                    if wait_time > 90:
                        st.session_state.waiting_queue = [item for item in st.session_state.waiting_queue if item["id"] != p["id"]]
                        st.session_state.equipment_status[eq] = None
                        st.rerun()
                    
                    st.markdown(f"""
                    <div class="status-card">
                        <b>⚙️ {eq}</b><br>
                        👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                        狀態: 等待開始...
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"▶️ 開始", key=f"start_{eq}"):
                        p["is_started"] = True
                        p["start_time"] = time.time()
                        p["current_set"] = 1
                        p["prompted_set"] = 0
                        st.rerun()
                
                else:
                    pres = p["prescription_detail"]
                    sets = pres["sets"]
                    set_time = pres["set_time"]
                    rest_time = pres["rest_time"]
                    
                    # 簡化狀態描述：只保留使用者與中斷休息等核心資訊
                    status_str = "🏋️ 訓練中"
                    if is_currently_paused:
                        remaining_pause = max(0, int(MID_PAUSE_SECONDS - (current_now - p["pause_start_time"])))
                        status_str = f"☕ 中斷休息中 (倒數: {remaining_pause}秒)"
                    elif is_in_rest:
                        rest_elapsed = int(current_now - p["rest_start_time"])
                        rem_rest = max(0, rest_time - rest_elapsed)
                        status_str = f"🔄 組間休息中 (剩餘: {rem_rest}秒)"
                    elif show_modal:
                        status_str = f"⚠️ 第 {p['current_set']} 組已達預定時間"

                    st.markdown(f"""
                    <div class="status-card" style="border-left: 5px solid {'#eab308' if is_currently_paused else '#10b981'};">
                        <b>⚙️ {eq}</b><br>
                        👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                        狀態: {status_str}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    if show_modal:
                        if c1.button(f"✅ 完成", key=f"conf_done_{eq}"):
                            p["show_target_reached_modal"] = False
                            p["prompted_set"] = p["current_set"]
                            if p["current_set"] >= sets:
                                if p["id"] not in st.session_state.patient_history:
                                    st.session_state.patient_history[p["id"]] = set()
                                st.session_state.patient_history[p["id"]].add(eq.split('_')[0])
                                st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
                                st.session_state.equipment_status[eq] = None
                            else:
                                p["is_in_rest_period"] = True
                                p["rest_start_time"] = time.time()
                            st.rerun()
                            
                        if c2.button(f"❌ 繼續", key=f"conf_not_yet_{eq}"):
                            p["show_target_reached_modal"] = False
                            p["prompted_set"] = p["current_set"] 
                            st.rerun()
                    elif is_in_rest:
                        if c1.button(f"▶️ 跳過休息", key=f"skip_rest_{eq}"):
                            p["is_in_rest_period"] = False
                            p["current_set"] += 1
                            p["start_time"] = time.time()
                            p["prompted_set"] = p["current_set"] - 1
                            st.rerun()
                        c2.empty()
                    else:
                        if is_currently_paused:
                            c1.button(f"⏳ 休息中", key=f"s_{eq}", disabled=True)
                            if c2.button(f"▶️ 恢復", key=f"f_{eq}__skip"):
                                p["is_paused"] = False
                                p["pause_start_time"] = 0
                                st.rerun()
                        else:
                            if c1.button(f"⏸️ 中斷休息", key=f"s_{eq}__btn"):
                                p["is_paused"] = True
                                p["pause_start_time"] = time.time()
                                st.rerun()
                            if c2.button(f"✅ 完成本組", key=f"force_done_set_{eq}"):
                                p["prompted_set"] = p["current_set"]
                                p["show_target_reached_modal"] = False
                                if p["current_set"] >= sets:
                                    if p["id"] not in st.session_state.patient_history:
                                        st.session_state.patient_history[p["id"]] = set()
                                    st.session_state.patient_history[p["id"]].add(eq.split('_')[0])
                                    st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
                                    st.session_state.equipment_status[eq] = None
                                else:
                                    p["is_in_rest_period"] = True
                                    p["rest_start_time"] = time.time()
                                st.rerun()
            else:
                st.markdown(f"""<div class="status-card" style="border-left: 5px solid #cbd5e1; color: #94a3b8; padding: 25px;"><b>⚙️ {eq}</b><br>🟢 空閒中</div>""", unsafe_allow_html=True)

# 安全控制的自動刷新
has_active = len(st.session_state.waiting_queue) > 0 or any(p is not None for p in st.session_state.equipment_status.values()) or len(st.session_state.cooldown_patients) > 0

if has_active:
    time.sleep(1)
    st.rerun()