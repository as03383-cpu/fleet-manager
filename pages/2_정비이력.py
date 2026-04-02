"""
pages/2_정비이력.py — 정비 이력 관리
"""

import streamlit as st
from utils.db import (
    get_maintenance, get_maint_record,
    insert_maintenance, update_maintenance, delete_maintenance,
    get_all_vehicles_simple
)
from utils.helpers import MAINT_TYPES, safe_int, fmt_won

st.set_page_config(page_title="정비 이력", page_icon="🔧", layout="wide")
st.title("🔧 정비 이력")

# ── 세션 상태 ────────────────────────────────────────────────
if "maint_edit_id"   not in st.session_state: st.session_state.maint_edit_id   = None
if "maint_show_form" not in st.session_state: st.session_state.maint_show_form = False
if "maint_confirm_del" not in st.session_state: st.session_state.maint_confirm_del = None
if "maint_filter_vid" not in st.session_state: st.session_state.maint_filter_vid = None

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
    st.session_state.maint_filter_vid = veh_options[selected_label]

# ── 상단 버튼 ────────────────────────────────────────────────
c1, c2 = st.columns([6, 1])
with c1:
    search = st.text_input("🔍 검색 (번호판·정비내용)", key="maint_search")
with c2:
    st.write("")
    st.write("")
    if st.button("➕ 정비 등록", type="primary", use_container_width=True):
        st.session_state.maint_show_form = True
        st.session_state.maint_edit_id   = None
        st.rerun()

# ── 정비이력 목록 ────────────────────────────────────────────
vid  = st.session_state.maint_filter_vid
rows = get_maintenance(vehicle_id=vid, search=search)

if not rows:
    st.info("정비 기록이 없습니다.")
else:
    st.caption(f"총 {len(rows)}건")

    hcols = st.columns([1.5, 1.5, 2, 1.5, 3, 1.2, 1.5, 2, 1, 1])
    for col, label in zip(hcols, [
        "정비일자","번호판","차량","정비유형","내용","비용","주행km","정비소","수정","삭제"
    ]):
        col.markdown(f"**{label}**")
    st.divider()

    for r in rows:
        rcols = st.columns([1.5, 1.5, 2, 1.5, 3, 1.2, 1.5, 2, 1, 1])
        rcols[0].write(r.get("maint_date","") or "-")
        rcols[1].write(r.get("plate",""))
        rcols[2].write(r.get("vehicle","") or "-")
        rcols[3].write(r.get("maint_type","") or "-")
        rcols[4].write(r.get("description","") or "-")
        rcols[5].write(fmt_won(r.get("cost",0)))
        km = r.get("mileage",0)
        rcols[6].write(f"{km:,}km" if km else "-")
        rcols[7].write(r.get("shop","") or "-")

        if rcols[8].button("✏️", key=f"medit_{r['id']}"):
            st.session_state.maint_edit_id   = r["id"]
            st.session_state.maint_show_form = True
            st.rerun()

        if rcols[9].button("🗑️", key=f"mdel_{r['id']}"):
            st.session_state.maint_confirm_del = r["id"]
            st.rerun()

# ── 삭제 확인 ────────────────────────────────────────────────
if st.session_state.maint_confirm_del:
    mid = st.session_state.maint_confirm_del
    rec = get_maint_record(mid)
    if rec:
        st.warning(f"⚠️ **{rec.get('maint_date','')} / {rec.get('maint_type','')}** 정비 기록을 삭제하시겠습니까?")
        dc1, dc2 = st.columns(2)
        if dc1.button("✅ 삭제 확인", type="primary"):
            delete_maintenance(mid)
            st.session_state.maint_confirm_del = None
            st.success("삭제되었습니다.")
            st.rerun()
        if dc2.button("취소"):
            st.session_state.maint_confirm_del = None
            st.rerun()

# ── 등록 / 수정 폼 ───────────────────────────────────────────
if st.session_state.maint_show_form:
    edit_id = st.session_state.maint_edit_id
    is_edit = edit_id is not None
    data    = get_maint_record(edit_id) if is_edit else {}

    st.divider()
    st.subheader("✏️ 정비 수정" if is_edit else "➕ 정비 등록")

    with st.form("maint_form"):
        # 차량 선택
        veh_labels = [f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip()
                      for v in vehicles]
        veh_ids    = [v["id"] for v in vehicles]

        preset_vid = data.get("vehicle_id", st.session_state.maint_filter_vid)
        try:
            preset_idx = veh_ids.index(preset_vid) if preset_vid else 0
        except ValueError:
            preset_idx = 0

        selected_veh = st.selectbox("차량 *", veh_labels, index=preset_idx)
        sel_vid = veh_ids[veh_labels.index(selected_veh)] if veh_labels else None

        fc1, fc2 = st.columns(2)
        maint_date  = fc1.text_input("정비일자 * (YYYY-MM-DD)", value=data.get("maint_date",""))
        mtype_idx   = MAINT_TYPES.index(data["maint_type"]) if data.get("maint_type") in MAINT_TYPES else 0
        maint_type  = fc2.selectbox("정비유형", MAINT_TYPES, index=mtype_idx)

        description = st.text_input("정비내용", value=data.get("description",""))

        gc1, gc2, gc3 = st.columns(3)
        cost      = gc1.text_input("비용(원)",   value=str(data.get("cost","") or ""))
        mileage   = gc2.text_input("주행km",     value=str(data.get("mileage","") or ""))
        shop      = gc3.text_input("정비소",     value=data.get("shop",""))
        next_date = st.text_input("다음 점검일 (YYYY-MM-DD)", value=data.get("next_date",""))
        notes     = st.text_area("메모", value=data.get("notes",""), height=80)

        sc1, sc2 = st.columns(2)
        submitted = sc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
        cancelled = sc2.form_submit_button("✖ 취소", use_container_width=True)

    if submitted:
        if not maint_date.strip():
            st.error("정비일자는 필수입니다.")
        elif not sel_vid:
            st.error("차량을 선택하세요.")
        else:
            save_data = dict(
                vehicle_id  = sel_vid,
                maint_date  = maint_date.strip(),
                maint_type  = maint_type,
                description = description.strip(),
                cost        = safe_int(cost),
                mileage     = safe_int(mileage),
                shop        = shop.strip(),
                next_date   = next_date.strip(),
                notes       = notes.strip(),
            )
            try:
                if is_edit:
                    update_maintenance(edit_id, save_data)
                    st.success("수정되었습니다.")
                else:
                    insert_maintenance(save_data)
                    st.success("등록되었습니다.")
                st.session_state.maint_show_form = False
                st.session_state.maint_edit_id   = None
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

    if cancelled:
        st.session_state.maint_show_form = False
        st.session_state.maint_edit_id   = None
        st.rerun()
