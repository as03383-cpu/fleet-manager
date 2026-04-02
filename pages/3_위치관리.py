"""
pages/3_위치관리.py — 위치 기록 관리
"""

import streamlit as st
from utils.db import (
    get_locations, insert_location, delete_location,
    get_all_vehicles_simple
)

st.set_page_config(page_title="위치 관리", page_icon="📍", layout="wide")
st.title("📍 위치 관리")

# ── 세션 상태 ────────────────────────────────────────────────
if "loc_show_form"    not in st.session_state: st.session_state.loc_show_form    = False
if "loc_filter_vid"   not in st.session_state: st.session_state.loc_filter_vid   = None
if "loc_confirm_del"  not in st.session_state: st.session_state.loc_confirm_del  = None

# ── 차량 선택 사이드바 ───────────────────────────────────────
vehicles = get_all_vehicles_simple()
veh_options = {"전체 보기": None}
for v in vehicles:
    label = f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip()
    veh_options[label] = v["id"]

with st.sidebar:
    st.markdown("### 차량 선택")
    selected_label = st.radio(
        "차량 선택",
        list(veh_options.keys()),
        label_visibility="collapsed"
    )
    st.session_state.loc_filter_vid = veh_options[selected_label]

# ── 상단 버튼 ────────────────────────────────────────────────
c1, c2 = st.columns([6, 1])
with c2:
    st.write("")
    if st.button("➕ 위치 등록", type="primary", use_container_width=True):
        st.session_state.loc_show_form = True
        st.rerun()

# ── 위치 목록 ────────────────────────────────────────────────
vid  = st.session_state.loc_filter_vid
rows = get_locations(vehicle_id=vid)

if not rows:
    st.info("위치 기록이 없습니다.")
else:
    st.caption(f"총 {len(rows)}건")

    hcols = st.columns([2, 1.5, 2.5, 4, 1])
    for col, label in zip(hcols, ["기록일시","번호판","위치명","메모","삭제"]):
        col.markdown(f"**{label}**")
    st.divider()

    for r in rows:
        rcols = st.columns([2, 1.5, 2.5, 4, 1])
        rcols[0].write(r.get("recorded_at","") or "-")
        rcols[1].write(r.get("plate",""))
        rcols[2].write(r.get("location_name","") or "-")
        rcols[3].write(r.get("notes","") or "-")
        if rcols[4].button("🗑️", key=f"ldel_{r['id']}"):
            st.session_state.loc_confirm_del = r["id"]
            st.rerun()

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

# ── 등록 폼 ──────────────────────────────────────────────────
if st.session_state.loc_show_form:
    st.divider()
    st.subheader("➕ 위치 등록")

    veh_labels = [f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip()
                  for v in vehicles]
    veh_ids    = [v["id"] for v in vehicles]

    with st.form("loc_form"):
        preset_vid = st.session_state.loc_filter_vid
        try:
            preset_idx = veh_ids.index(preset_vid) if preset_vid else 0
        except ValueError:
            preset_idx = 0

        selected_veh  = st.selectbox("차량 *", veh_labels, index=preset_idx)
        sel_vid        = veh_ids[veh_labels.index(selected_veh)] if veh_labels else None

        lc1, lc2 = st.columns(2)
        location_name = lc1.text_input("위치명")
        address       = lc2.text_input("주소")
        driver        = st.text_input("담당자")
        notes         = st.text_area("메모", height=80)

        sc1, sc2 = st.columns(2)
        submitted = sc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
        cancelled = sc2.form_submit_button("✖ 취소", use_container_width=True)

    if submitted:
        if not sel_vid:
            st.error("차량을 선택하세요.")
        else:
            try:
                insert_location(dict(
                    vehicle_id    = sel_vid,
                    location_name = location_name.strip(),
                    address       = address.strip(),
                    driver        = driver.strip(),
                    notes         = notes.strip(),
                ))
                st.success("등록되었습니다.")
                st.session_state.loc_show_form = False
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

    if cancelled:
        st.session_state.loc_show_form = False
        st.rerun()
