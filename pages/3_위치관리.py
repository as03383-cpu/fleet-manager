"""pages/3_위치관리.py — 위치 기록 관리"""

import streamlit as st
from datetime import datetime, timezone, timedelta
from utils.db import (
    get_locations, get_location, insert_location,
    update_location, delete_location,
    get_all_vehicles_simple,
)
from utils.helpers import MOBILE_CSS

def _fmt_kst(ts):
    """UTC 타임스탬프 → KST(UTC+9), YYYY-MM-DD HH:MM 형식"""
    if not ts:
        return "-"
    try:
        KST = timezone(timedelta(hours=9))
        dt  = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)[:16]

st.set_page_config(page_title="위치 관리", page_icon="📍", layout="wide")
st.markdown(MOBILE_CSS, unsafe_allow_html=True)
st.title("📍 위치 관리")

PAGE_SIZE = 100

# ── 세션 초기화 ───────────────────────────────────────────────
for k, v in [
    ("loc_show_form",    False),
    ("loc_edit_id",      None),
    ("loc_filter_vid",   None),
    ("loc_confirm_del",  None),
    ("loc_page",         0),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── 사이드바: 차량 선택 ───────────────────────────────────────
vehicles    = get_all_vehicles_simple()
veh_options = {"전체 보기": None}
for v in vehicles:
    veh_options[f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip()] = v["id"]

with st.sidebar:
    st.markdown("### 차량 선택")
    sel_label = st.radio("차량 선택", list(veh_options.keys()), label_visibility="collapsed")
    new_vid   = veh_options[sel_label]
    if new_vid != st.session_state.loc_filter_vid:
        st.session_state.loc_filter_vid = new_vid
        st.session_state.loc_page = 0

# ── 등록 버튼 ────────────────────────────────────────────────
c1, c2 = st.columns([6, 1])
c2.write("")
if c2.button("➕ 위치 등록", type="primary", use_container_width=True):
    st.session_state.loc_show_form = True
    st.session_state.loc_edit_id   = None

# ── 등록 / 수정 폼 (버튼 바로 아래) ──────────────────────────
if st.session_state.loc_show_form:
    edit_id = st.session_state.loc_edit_id
    is_edit = edit_id is not None
    data    = get_location(edit_id) if is_edit else {}

    st.divider()
    st.subheader("✏️ 위치 수정" if is_edit else "➕ 위치 등록")

    veh_labels = [f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip() for v in vehicles]
    veh_ids    = [v["id"] for v in vehicles]
    preset_vid = data.get("vehicle_id", st.session_state.loc_filter_vid)
    try:    preset_idx = veh_ids.index(preset_vid) if preset_vid else 0
    except: preset_idx = 0

    with st.form("loc_form"):
        selected_veh  = st.selectbox("차량 *", veh_labels, index=preset_idx)
        sel_vid       = veh_ids[veh_labels.index(selected_veh)] if veh_labels else None

        lc1, lc2 = st.columns(2)
        location_name = lc1.text_input("위치명", value=data.get("location_name",""))
        address       = lc2.text_input("주소",   value=data.get("address",""))
        driver        = st.text_input("담당자",  value=data.get("driver",""))
        notes         = st.text_area("메모", value=data.get("notes",""), height=80)

        sc1, sc2  = st.columns(2)
        submitted = sc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
        cancelled = sc2.form_submit_button("✖ 취소", use_container_width=True)

    if submitted:
        if not sel_vid:
            st.error("차량을 선택하세요.")
        else:
            save_data = dict(
                vehicle_id=sel_vid, location_name=location_name.strip(),
                address=address.strip(), driver=driver.strip(), notes=notes.strip(),
            )
            try:
                if is_edit: update_location(edit_id, save_data)
                else:       insert_location(save_data)
                st.success("수정되었습니다." if is_edit else "등록되었습니다.")
                st.session_state.loc_show_form = False
                st.session_state.loc_edit_id   = None
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

    if cancelled:
        st.session_state.loc_show_form = False
        st.session_state.loc_edit_id   = None
        st.rerun()

    st.divider()

# ── 위치 목록 ────────────────────────────────────────────────
all_rows = get_locations(vehicle_id=st.session_state.loc_filter_vid)

if not all_rows:
    st.info("위치 기록이 없습니다.")
else:
    total_count = len(all_rows)
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(st.session_state.loc_page, total_pages - 1)
    st.session_state.loc_page = page

    def page_nav(suffix):
        n1, n2, n3 = st.columns([1, 3, 1])
        if n1.button("◀ 이전", disabled=(page==0), use_container_width=True, key=f"lprev_{suffix}"):
            st.session_state.loc_page = page - 1; st.rerun()
        n2.markdown(
            f"<div style='text-align:center;padding:8px;color:#94a3b8'>"
            f"페이지 {page+1}/{total_pages}  (전체 {total_count}건)</div>",
            unsafe_allow_html=True,
        )
        if n3.button("다음 ▶", disabled=(page>=total_pages-1), use_container_width=True, key=f"lnext_{suffix}"):
            st.session_state.loc_page = page + 1; st.rerun()

    if total_pages > 1: page_nav("top")
    else: st.caption(f"총 {total_count}건")

    COL = [2, 1.5, 2.5, 4, 0.7, 0.7]
    for col, label in zip(st.columns(COL), ["기록일시","번호판","위치명","메모","수정","삭제"]):
        col.markdown(f"**{label}**")
    st.divider()

    rows = all_rows[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    for r in rows:
        rc = st.columns(COL)
        rc[0].write(_fmt_kst(r.get("recorded_at","")))
        rc[1].write(r.get("plate",""))
        rc[2].write(r.get("location_name","") or "-")
        rc[3].write(r.get("notes","") or "-")

        if rc[4].button("✏️", key=f"ledit_{r['id']}", help="수정"):
            st.session_state.loc_edit_id   = r["id"]
            st.session_state.loc_show_form = True
            st.rerun()
        if rc[5].button("🗑️", key=f"ldel_{r['id']}", help="삭제"):
            st.session_state.loc_confirm_del = r["id"]
            st.rerun()

    if total_pages > 1: page_nav("bot")

# ── 삭제 확인 ────────────────────────────────────────────────
if st.session_state.loc_confirm_del:
    lid = st.session_state.loc_confirm_del
    st.warning("⚠️ 이 위치 기록을 삭제하시겠습니까?")
    dc1, dc2 = st.columns(2)
    if dc1.button("✅ 삭제 확인", type="primary"):
        delete_location(lid)
        st.session_state.loc_confirm_del = None
        st.success("삭제되었습니다.")
        st.rerun()
    if dc2.button("취소"):
        st.session_state.loc_confirm_del = None
        st.rerun()
