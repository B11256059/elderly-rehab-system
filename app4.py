import streamlit as st
import pandas as pd
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
        border-left: 5px solid #10b981; 
        background-color: #f0fdf4;
    }
    .waiting-row { font-size: 0.9em; padding: 10px; border-bottom: 1px solid #e2e8f0; }
    .highlight-text { color: #0e7490; font-weight: bold; }
    .warning-text { color: #b45309; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 智慧復健動態排程管理系統")

# ==========================================
# 2. 原始復健運動處方大表與固定長輩資料庫
# ==========================================
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
    
        # 器材四: 肩關節康復器
        {"器材": "肩關節康復器", "年齡": 60, "組數": 5, "次數": 20, "組時間": "45 (AI推估)", "休息時間": "60 (參考ACSM)"},
        {"器材": "肩關節康復器", "年齡": 70, "組數": 4, "次數": 16, "組時間": "38 (AI推估)", "休息時間": "70 (參考ACSM)"},
        {"器材": "肩關節康復器", "年齡": 80, "組數": 3, "次數": 13, "組時間": "32 (AI推估)", "休息時間": "80 (參考ACSM)"},
        {"器材": "肩關節康復器", "年齡": 90, "組數": 3, "次數": 10, "組時間": "28 (AI推估)", "休息時間": "90 (參考ACSM)"},
    
        # 器材五: 復健助行車
        {"器材": "復健助行車", "年齡": 60, "組數": 2, "次數": "不適用", "組時間": 300, "休息時間": "60 (參考ACSM)"},
        {"器材": "復健助行車", "年齡": 70, "組數": 4, "次數": "不適用", "組時間": 300, "休息時間": "70 (參考ACSM)"},
        {"器材": "復健助行車", "年齡": 80, "組數": 6, "次數": "不適用", "組時間": 300, "休息時間": "80 (參考ACSM)"},
        {"器材": "復健助行車", "年齡": 90, "組數": 8, "次數": "不適用", "組時間": 300, "休息時間": "90 (參考ACSM)"},
]

lookup_table = {}
prescription_details = {}

for item in raw_data:
    sets = int(item["組數"])
    set_time = int(item["組時間"])
    rest_time = int(item["休息時間"])
    
    total_seconds = (set_time * sets) + (rest_time * (sets - 1)) if sets > 1 else set_time * sets
    total_minutes = max(1, round(total_seconds / 60))
    
    lookup_table[(item["器材"], item["年齡"])] = total_minutes
    prescription_details[(item["器材"], item["年齡"])] = {
        "sets": sets, "set_time": set_time, "rest_time": rest_time
    }

# 初始化 10 位長輩固定處方資料庫
if "PATIENT_DATABASE" not in st.session_state:
    st.session_state.PATIENT_DATABASE = {
        "1101 2203 4401": {"id": 1, "last_name": "王", "title": "爺爺", "age": 80, "equips": ["大轉輪", "坐推"]},
        "1101 2203 4402": {"id": 2, "last_name": "陳", "title": "奶奶", "age": 70, "equips": ["漫步機"]},
        "1101 2203 4403": {"id": 3, "last_name": "林", "title": "爺爺", "age": 90, "equips": ["肩關節康復器", "復健助行車", "大轉輪"]},
        "1101 2203 4404": {"id": 4, "last_name": "張", "title": "奶奶", "age": 60, "equips": ["坐推", "漫步機"]},
        "1101 2203 4405": {"id": 5, "last_name": "李", "title": "爺爺", "age": 80, "equips": ["復健助行車"]},
        "1101 2203 4406": {"id": 6, "last_name": "吳", "title": "奶奶", "age": 70, "equips": ["大轉輪", "肩關節康復器"]},
        "1101 2203 4407": {"id": 7, "last_name": "劉", "title": "爺爺", "age": 90, "equips": ["坐推", "漫步機", "肩關節康復器"]},
        "1101 2203 4408": {"id": 8, "last_name": "蔡", "title": "奶奶", "age": 60, "equips": ["大轉輪", "復健助行車", "漫步機", "坐推"]},
        "1101 2203 4409": {"id": 9, "last_name": "楊", "title": "爺爺", "age": 80, "equips": ["肩關節康復器"]},
        "1101 2203 4410": {"id": 10, "last_name": "黃", "title": "奶奶", "age": 90, "equips": ["大轉輪", "坐推", "漫步機"]}
    }

PATIENT_DATABASE = st.session_state.PATIENT_DATABASE
NORMALIZED_DB = {k.replace(" ", ""): (k, v) for k, v in PATIENT_DATABASE.items()}

# ==========================================
# 3. 系統狀態初始化
# ==========================================
if "active_patients" not in st.session_state: st.session_state.active_patients = {}
if "waiting_queue" not in st.session_state: st.session_state.waiting_queue = []  
if "patient_groups" not in st.session_state: st.session_state.patient_groups = {} 
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
if "patient_history" not in st.session_state: st.session_state.patient_history = {}
if "scanned_cards" not in st.session_state: st.session_state.scanned_cards = set()

TRANSIT_COOLDOWN_SECONDS = 180 
MID_PAUSE_SECONDS = 60          

# ==========================================
# 4. 功能函數：加入刷卡與多項處方初始化
# ==========================================
def add_patient_by_card(raw_card_key):
    orig_key, p_info = NORMALIZED_DB[raw_card_key]
    p_id = p_info["id"]
    
    st.session_state.active_patients[p_id] = {
        "info": p_info,
        "completed_equips": set(),
        "origin_key": orig_key
    }
    st.session_state.scanned_cards.add(orig_key)
    
    for equip in p_info["equips"]:
        pres_info = prescription_details.get((equip, p_info["age"]), {"sets": 3, "set_time": 30, "rest_time": 60})
        st.session_state.waiting_queue.append({
            "id": p_id, "name": f"{p_info['last_name']}{p_info['title']}", "age": p_info['age'],
            "target_equip": equip, "arrival_time": time.time(),
            "service_time": lookup_table.get((equip, p_info["age"]), 5),
            "prescription_detail": pres_info,
            "is_paused": False,      
            "pause_start_time": 0,      
            "total_paused_duration": 0  
        })

# ==========================================
# 5. 側邊欄：刷卡模擬與長輩名單
# ==========================================
with st.sidebar:
    st.header("📇 模擬刷健保卡區")
    st.write("點擊下方長輩按鈕模擬刷卡報到：")
    
    for c_id, info in PATIENT_DATABASE.items():
        btn_label = f"👤 [{c_id}] {info['last_name']}{info['title']} ({info['age']}歲)"
            
        if st.button(btn_label, key=f"btn_{c_id}"):
            norm_id = c_id.replace(" ", "")
            if c_id not in st.session_state.scanned_cards:
                add_patient_by_card(norm_id)
                st.success(f"✅ 辨識成功！{info['last_name']}{info['title']} 已完成報到並進入排程系統！")
                st.rerun()
            else:
                st.warning(f"⚠️ {info['last_name']}{info['title']} 已經報到或正在進行中！")
                
    st.write("---")
    if st.button("🧹 清空所有數據並重置"):
        st.session_state.waiting_queue = []
        st.session_state.active_patients = {}
        st.session_state.equipment_status = {eq: None for eq in st.session_state.equipment_status.keys()}
        st.session_state.cooldown_patients = {}
        st.session_state.patient_history = {}
        st.session_state.scanned_cards = set()
        st.session_state.start_system_timestamp = time.time()
        
        st.session_state.PATIENT_DATABASE = {
            "1101 2203 4401": {"id": 1, "last_name": "王", "title": "爺爺", "age": 80, "equips": ["大轉輪", "坐推"]},
            "1101 2203 4402": {"id": 2, "last_name": "陳", "title": "奶奶", "age": 70, "equips": ["漫步機"]},
            "1101 2203 4403": {"id": 3, "last_name": "林", "title": "爺爺", "age": 90, "equips": ["肩關節康復器", "復健助行車", "大轉輪"]},
            "1101 2203 4404": {"id": 4, "last_name": "張", "title": "奶奶", "age": 60, "equips": ["坐推", "漫步機"]},
            "1101 2203 4405": {"id": 5, "last_name": "李", "title": "爺爺", "age": 80, "equips": ["復健助行車"]},
            "1101 2203 4406": {"id": 6, "last_name": "吳", "title": "奶奶", "age": 70, "equips": ["大轉輪", "肩關節康復器"]},
            "1101 2203 4407": {"id": 7, "last_name": "劉", "title": "爺爺", "age": 90, "equips": ["坐推", "漫步機", "肩關節康復器"]},
            "1101 2203 4408": {"id": 8, "last_name": "蔡", "title": "奶奶", "age": 60, "equips": ["大轉輪", "復健助行車", "漫步機", "坐推"]},
            "1101 2203 4409": {"id": 9, "last_name": "楊", "title": "爺爺", "age": 80, "equips": ["肩關節康復器"]},
            "1101 2203 4410": {"id": 10, "last_name": "黃", "title": "奶奶", "age": 90, "equips": ["大轉輪", "坐推", "漫步機"]}
        }
        st.rerun()

# ==========================================
# 5.5 顯示原始復健運動處方大表 (編號改為 1-20)
# ==========================================
with st.expander("📋 點此檢視：復健運動處方大表", expanded=False):
    df_raw = pd.DataFrame(raw_data)
    # 將預設的 index (0-19) 改成從 1 開始計算的編號 (1-20)
    df_raw.index = range(1, len(df_raw) + 1)
    df_raw.index.name = "序號"
    
    df_raw = df_raw.rename(columns={"器材名稱": "器材名稱", "年齡層": "年齡層", "組數": "組數", "次數": "次數", "組時間": "組時間", "休息時間": "休息時間"})
    st.dataframe(df_raw, use_container_width=True)

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
m3.metric("換場休息中", f"{len(st.session_state.cooldown_patients)} 人")

# 健保卡號手動/條碼槍輸入區
with st.container():
    st.info("💡 **櫃台刷卡區**：請使用條碼槍或輸入健保卡號後按 Enter。")
    card_input = st.text_input("健保卡號輸入框", placeholder="請刷入健保卡號...", key="card_scanner_input")
    if card_input:
        cleaned_card = card_input.strip().replace(" ", "").replace("-", "")
        if cleaned_card in NORMALIZED_DB:
            orig_key, p_info = NORMALIZED_DB[cleaned_card]
            if orig_key not in st.session_state.scanned_cards:
                add_patient_by_card(cleaned_card)
                st.success(f"✅ 辨識成功！{p_info['last_name']}{p_info['title']} 已完成報到，共帶入 {len(p_info['equips'])} 項處方！")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning(f"⚠️ {p_info['last_name']}{p_info['title']} 已經報到或正在進行中！")
        else:
            st.error(f"❌ 找不到對應的健保卡號，請確認是否正確。")

# --- 核心調度邏輯 ---
now = time.time()
need_trigger_rerun = False 

for eq, p in list(st.session_state.equipment_status.items()):
    if p:
        if p.get("is_paused", False):
            if now - p["pause_start_time"] >= MID_PAUSE_SECONDS:
                p["total_paused_duration"] += MID_PAUSE_SECONDS
                p["is_paused"] = False
                p["pause_start_time"] = 0
                need_trigger_rerun = True
            else:
                continue

        if p.get("is_in_rest_period", False):
            rest_elapsed = now - p["rest_start_time"]
            pres = p["prescription_detail"]
            if rest_elapsed >= pres["rest_time"]:
                p["is_in_rest_period"] = False
                p["current_set"] += 1
                p["start_time"] = time.time()
                p["total_paused_duration"] = 0
                p["prompted_set"] = p["current_set"] - 1
                need_trigger_rerun = True
            else:
                need_trigger_rerun = True  
            continue

        if p.get("show_target_reached_modal", False):
            continue

        net_active_seconds = now - p["start_time"] - p.get("total_paused_duration", 0)
        pres = p["prescription_detail"]
        sets = pres["sets"]
        set_time = pres["set_time"]
        
        if "current_set" not in p: p["current_set"] = 1
        if "prompted_set" not in p: p["prompted_set"] = 0

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
        
        if available_eqs and p["id"] not in busy_ids and not is_cd:
            eq = available_eqs[0]
            p["start_time"] = now
            p["show_target_reached_modal"] = False
            p["current_set"] = 1
            p["prompted_set"] = 0
            p["is_in_rest_period"] = False
            st.session_state.equipment_status[eq] = p
            busy_ids.add(p["id"])
            need_trigger_rerun = True
        else:
            rem_waiting.append(p)
            
    st.session_state.waiting_queue = rem_waiting
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
                        p["current_set"] = 1
                        p["prompted_set"] = 0
                        st.rerun()
                
                else:
                    pres = p["prescription_detail"]
                    sets = pres["sets"]
                    set_time = pres["set_time"]
                    rest_time = pres["rest_time"]
                    
                    # 狀態 A: 正在組間休息
                    if is_in_rest:
                        rest_elapsed = int(current_now - p["rest_start_time"])
                        rem_rest = max(0, rest_time - rest_elapsed)
                        st.markdown(f"""
                        <div class="status-card" style="background-color: #f0fdf4; border-left: 5px solid #22c55e;">
                            <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                            👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                            🔄 <span style="color:#15803d; font-weight:bold;">組間休息中</span> (剩餘: {rem_rest} 秒)
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"▶️ 跳過休息，進行下一組", key=f"skip_rest_{eq}"):
                            p["is_in_rest_period"] = False
                            p["current_set"] += 1
                            p["start_time"] = time.time()
                            p["total_paused_duration"] = 0
                            p["prompted_set"] = p["current_set"] - 1
                            st.rerun()

                    # 狀態 B: 達到設定時間，跳出彈窗
                    elif show_modal:
                        net_active_sec = int(current_now - p["start_time"] - p.get("total_paused_duration", 0))
                        st.markdown(f"""
                        <div class="status-card" style="background-color: #fef3c7; border-left: 5px solid #d97706;">
                            <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                            👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                            ⚠️ <span style="color:#b45309; font-weight:bold;">第 {p['current_set']} 組已達預定時間！</span><br>
                            請問本組是否已完成？
                        </div>
                        """, unsafe_allow_html=True)
                        
                        c1, c2 = st.columns(2)
                        if c1.button(f"✅ 已完成 (進入休息)", key=f"conf_done_{eq}"):
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
                            
                        if c2.button(f"❌ 尚未完成 (繼續訓練)", key=f"conf_not_yet_{eq}"):
                            p["show_target_reached_modal"] = False
                            p["prompted_set"] = p["current_set"]  
                            st.rerun()

                    # 狀態 C: 正常訓練中
                    else:
                        if is_currently_paused:
                            remaining_pause = max(0, int(MID_PAUSE_SECONDS - (current_now - p["pause_start_time"])))
                            st.markdown(f"""
                            <div class="status-card paused">
                                <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                                👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                                ⏱️ 中斷休息中 <span class="warning-text">(倒數: {remaining_pause}秒)</span>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            net_active_sec = int(current_now - p["start_time"] - p.get("total_paused_duration", 0))
                            
                            st.markdown(f"""
                            <div class="status-card">
                                <b style='font-size:1.2em;'>⚙️ {eq}</b><br>
                                👤 使用者: <span class="highlight-text">{p['name']} ({p['age']}歲) [#{p['id']:03d}]</span><br>
                                🏋️ 正在執行: 第 {p['current_set']}/{sets} 組訓練<br>
                                ⏱️ 淨執行時間: {net_active_sec}秒 / 單組預定: {set_time}秒
                            </div>
                            """, unsafe_allow_html=True)
                        
                        c1, c2 = st.columns(2)
                        if is_currently_paused:
                            c1.button(f"⏳ 休息中", key=f"s_{eq}", disabled=True)
                            if c2.button(f"▶️ 跳過休息", key=f"f_{eq}__skip"):
                                p["total_paused_duration"] += (time.time() - p["pause_start_time"])
                                p["is_paused"] = False
                                p["pause_start_time"] = 0
                                st.rerun()
                        else:
                            if c1.button(f"⏸️ 中斷休息", key=f"s_{eq}__btn"):
                                p["is_paused"] = True
                                p["pause_start_time"] = time.time()
                                st.rerun()
                            if c2.button(f"✅ 已完成此組", key=f"force_done_set_{eq}@@"):
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