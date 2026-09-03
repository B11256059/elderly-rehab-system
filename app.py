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
    .status-card.auto-resting {
        border-left: 5px solid #3b82f6; 
        background-color: #eff6ff;
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
            "total_paused_duration": 0,  
            "group_id": group_id,
            "manual_current_set": 1  # 追蹤手動/手札點擊的目前組數
        })

# ==========================================
# 5. 側邊欄模擬與控制
# ==========================================
with st.sidebar:
    st.header("👥 模擬情境")
    st.write(f"當前已模擬人數: {st.session_state.total_mock_count} / 20")
    
    if st.button("🚀 分批注入 (自動隨機單人/多人同行)"):
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
    st.info(f"💡 提示：下一位獨立報到的長輩系統編號為 **#{next_preview_id}**。")

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
        
        input_equips = st.multiselect("復健處方器材 (可多選 1~3 項)", ["大轉輪", "坐推", "漫步機", "肩關節康復器", "復健助行車"], default=st.session_state.input_equips, key=f"eqs_widget_{st.session_state.form_version}")
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
                p["total_paused_duration"] += MID_PAUSE_SECONDS
                p["is_paused"] = False
                p["pause_start_time"] = 0
            else:
                continue

        net_active_seconds = now - p["start_time"] - p.get("total_paused_duration", 0)
        
        pres = p["prescription_detail"]
        sets = pres["sets"]
        set_time = pres["set_time"]
        rest_time = pres["rest_time"]
        
        if sets <= 1:
            total_required_seconds = set_time
        else:
            total_required_seconds = (set_time * sets) + (rest_time * (sets - 1))
            
        if net_active_seconds >= total_required_seconds:
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
                            comp["start_time"] = now
                            st.session_state.equipment_status[eq_to_assign] = comp
                            busy_ids.add(comp["id"])
                    assigned = True
                    need_trigger_rerun = True
            
            if not assigned:
                eq = available_eqs[0]
                p["start_time"] = now
                st.session_state.equipment_status[eq] = p
                busy_ids.add(p["id"])
                need_trigger_rerun = True
        else:
            rem_waiting.append(p)
            
    st.session_state.waiting_queue = [p for p in rem_waiting if p["id"] not in busy_ids]

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
        now = time.time()
        display_data = []
        for p in st.session_state.waiting_queue:
            wait_seconds = int(now - p["arrival_time"])
            id_str = f"#{p['id']:03d}"
            
            p_id = p["id"]
            if p_id in st.session_state.patient_groups:
                group_members = st.session_state.patient_groups[p_id]
                other_members = [f"#{m:03d}" for m in group_members if m != p_id]
                group_str = ", ".join(other_members) if other_members else "-"
            else:
                group_str = f"#{p['group_id']:03d}" if p.get("group_id") else "-"
            
            display_data.append({
                "長輩編號": id_str,
                "姓名": p["name"],
                "年齡": f"{p['age']}歲",
                "目標器材": p["target_equip"],
                "同行組別": group_str,
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
                
                if not p.get("is_started", False):
                    if "assigned_time" not in p: p["assigned_time"] = time.time()
                    wait_time = current_now - p.get("assigned_time", current_now)
                    
                    if wait_time > 90:
                        st.session_state.waiting_queue = [item for item in st.session_state.waiting_queue if item["id"] != p["id"]]
                        st.session_state.equipment_status[eq] = None
                        st.rerun()
                    
                    bg_color = "#fee2e2" if wait_time > 60 else "#eff6ff"
                    border_color = "#ef4444" if wait_time > 60 else "#3b82f6"
                    status_text = f'⏳ 逾時自動釋放倒數: {int(90 - wait_time)}秒' if wait_time > 60 else '等待開始復健...'
                    
                    st.markdown(f"""
                    <div class="status-card" style="background-color: {bg_color}; border-left: 5px solid {border_color};">
                        <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                        👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                        狀態: <span style="color:{'#b91c1c' if wait_time > 60 else '#1d4ed8'}; font-weight:bold;">{status_text}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"▶️ 開始復健", key=f"start_{eq}"):
                        p["is_started"] = True
                        p["start_time"] = time.time()
                        p["manual_current_set"] = 1  # 初始化從第1組開始
                        st.rerun()
                
                else:
                    net_active_sec = int(current_now - p["start_time"] - p.get("total_paused_duration", 0))
                    pres = p["prescription_detail"]
                    sets = pres["sets"]
                    set_time = pres["set_time"]
                    rest_time = pres["rest_time"]
                    
                    is_auto_resting = False
                    time_based_set_num = 1
                    auto_rest_left = 0
                    
                    if sets > 1:
                        cycle_time = set_time + rest_time
                        current_cycle_pos = net_active_sec % cycle_time
                        time_based_set_num = min(sets, (net_active_sec // cycle_time) + 1)
                        
                        if time_based_set_num < sets and current_cycle_pos >= set_time:
                            is_auto_resting = True
                            auto_rest_left = max(0, rest_time - (current_cycle_pos - set_time))
                    
                    # 融合自動進度與手動點擊進度（取其最大值，確保手動點擊後能正確遞增）
                    current_set_num = max(time_based_set_num, p.get("manual_current_set", 1))
                    if current_set_num > sets:
                        current_set_num = sets
                    
                    # 判斷動態按鈕文字：如果已經是最後一組，顯示「已完成目標」，否則顯示「第 X 組已完成」
                    if current_set_num >= sets:
                        done_button_label = "🐇 已完成目標"
                    else:
                        done_button_label = f"🐇 第 {current_set_num} 組已完成"
                    
                    if is_currently_paused:
                        remaining_pause = max(0, int(MID_PAUSE_SECONDS - (current_now - p["pause_start_time"])))
                        st.markdown(f"""
                        <div class="status-card paused">
                            <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                            👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                            ⏱️ 手動中斷休息中 <span class="warning-text">(倒數: {remaining_pause}秒)</span>
                        </div>
                        """, unsafe_allow_html=True)
                    elif is_auto_resting:
                        st.markdown(f"""
                        <div class="status-card auto-resting">
                            <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                            👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                            🔄 <span style="color:#2563eb; font-weight:bold;">組間自動休息中</span> (第 {current_set_num}/{sets} 組完成)<br>
                            ⏳ 休息倒數: <span class="warning-text">{auto_rest_left} 秒</span> / 預計總處方: {p['service_time']}分鐘
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="status-card">
                            <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                            👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                            🏋️ 正在執行: 第 {current_set_num}/{sets} 組訓練<br>
                            ⏱️ 淨執行時間: {net_active_sec//60}分{net_active_sec%60}秒 / 處方預計: {p['service_time']}分鐘
                        </div>
                        """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    
                    if is_currently_paused:
                        c1.button(f"⏳ 休息中...", key=f"s_{eq}", disabled=True)
                        if c2.button(f"▶️ 跳過休息", key=f"f_{eq}__skip"):
                            p["total_paused_duration"] += (time.time() - p["pause_start_time"])
                            p["is_paused"] = False
                            p["pause_start_time"] = 0
                            st.rerun()
                    elif is_auto_resting:
                        c1.button(f"🔄 組間休息中", key=f"s_{eq}_auto", disabled=True)
                        if c2.button(done_button_label, key=f"f_{eq}__done"):
                            if current_set_num >= sets:
                                if p["id"] not in st.session_state.patient_history:
                                    st.session_state.patient_history[p["id"]] = set()
                                st.session_state.patient_history[p["id"]].add(eq.split('_')[0])
                                st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
                                st.session_state.equipment_status[eq] = None
                            else:
                                p["manual_current_set"] = current_set_num + 1
                            st.rerun()
                    else:
                        if c1.button(f"⏸️ 手動中斷 (1分)", key=f"s_{eq}__btn"):
                            p["is_paused"] = True
                            p["pause_start_time"] = time.time()
                            st.rerun()
                        if c2.button(done_button_label, key=f"f_{eq}__done"):
                            if current_set_num >= sets:
                                if p["id"] not in st.session_state.patient_history:
                                    st.session_state.patient_history[p["id"]] = set()
                                st.session_state.patient_history[p["id"]].add(eq.split('_')[0])
                                st.session_state.cooldown_patients[p["id"]] = time.time() + TRANSIT_COOLDOWN_SECONDS
                                st.session_state.equipment_status[eq] = None
                            else:
                                p["manual_current_set"] = current_set_num + 1
                            st.rerun()
            else:
                st.markdown(f"""<div class="status-card" style="border-left: 5px solid #cbd5e1; color: #94a3b8; padding: 25px;"><b>⚙️ {eq}</b><br>🟢 空閒中</div>""", unsafe_allow_html=True)

has_active = len(st.session_state.waiting_queue) > 0 or any(p is not None for p in st.session_state.equipment_status.values()) or len(st.session_state.cooldown_patients) > 0

if has_active:
    time.sleep(1)
    st.rerun()