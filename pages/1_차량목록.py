"""
pages/1_차량목록.py — 차량 목록 / 등록 / 수정 / 삭제
"""

import streamlit as st
from utils.db import (
    get_vehicles, get_vehicle, insert_vehicle,
    update_vehicle, delete_vehicle, get_all_vehicles_simple
)
from utils.helpers import (
    STATUS_LIST, FUEL_TYPES, STATUS_COLORS,
    safe_int, fmt_km_mi, fmt_won
)

st.set_page_config(page_title="차량 목록", page_icon="🚗", layout="wide")
st.title("🚗 차량 목록")

# ── 세션 상태 초기화 ─────────────────────────────────────────
if "veh_edit_id"   not in st.session_state: st.session_state.veh_edit_id   = None
if "veh_show_form" not in st.session_state: st.session_state.veh_show_form = False
if "veh_confirm_del" not in st.session_state: st.session_state.veh_confirm_del = None

# ── 검색 / 필터 바 ───────────────────────────────────────────
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    search = st.text_input("🔍 검색 (번호판·제조사·모델·스톡넘버)", key="veh_search")
with c2:
    status_filter = st.selectbox("상태 필터", ["전체"] + STATUS_LIST, key="veh_status_filter")
with c3:
    st.write("")
    st.write("")
    if st.button("➕ 차량 등록", use_container_width=True, type="primary"):
        st.session_state.veh_show_form = True
        st.session_state.veh_edit_id   = None

# ── 환율 설정 ────────────────────────────────────────────────
with st.expander("💱 환율 설정"):
    rate = st.number_input("USD 환율 (원/USD)", value=1350, min_value=100, max_value=5000, step=10)

# ── 차량 목록 표시 ───────────────────────────────────────────
rows = get_vehicles(search=search, status_filter=status_filter)

if not rows:
    st.info("조건에 맞는 차량이 없습니다.")
else:
    st.caption(f"총 {len(rows)}대")

    # 헤더
    hcols = st.columns([1.2, 1.5, 1.2, 1, 1.2, 0.8, 2, 1.5, 1.2, 1.2, 1.2, 1.5, 1, 1])
    for col, label in zip(hcols, [
        "스톡넘버","번호판","제조사","담당자","모델","연식",
        "주행거리","상태","구매일","등록일","판매일","판매자명","수정","삭제"
    ]):
        col.markdown(f"**{label}**")

    st.divider()

    for r in rows:
        status = r.get("status","")
        color  = STATUS_COLORS.get(status, "#94a3b8")
        rcols  = st.columns([1.2, 1.5, 1.2, 1, 1.2, 0.8, 2, 1.5, 1.2, 1.2, 1.2, 1.5, 1, 1])

        rcols[0].write(r.get("stock_number") or "-")
        rcols[1].write(r.get("plate",""))
        rcols[2].write(r.get("make","") or "-")
        rcols[3].write(r.get("driver","") or "-")
        rcols[4].write(r.get("model","") or "-")
        rcols[5].write(str(r.get("year","")) or "-")
        rcols[6].write(fmt_km_mi(r.get("mileage", 0)))
        rcols[7].markdown(
            f'<span style="color:{color};font-weight:bold">{status}</span>',
            unsafe_allow_html=True
        )
        rcols[8].write(r.get("purchase_date","") or "-")
        rcols[9].write(r.get("reg_date","") or "-")
        rcols[10].write(r.get("sale_date","") or "-")
        rcols[11].write(r.get("seller_name","") or "-")

        if rcols[12].button("✏️", key=f"edit_{r['id']}", help="수정"):
            st.session_state.veh_edit_id   = r["id"]
            st.session_state.veh_show_form = True
            st.rerun()

        if rcols[13].button("🗑️", key=f"del_{r['id']}", help="삭제"):
            st.session_state.veh_confirm_del = r["id"]
            st.rerun()

# ── 삭제 확인 ────────────────────────────────────────────────
if st.session_state.veh_confirm_del:
    vid = st.session_state.veh_confirm_del
    v   = get_vehicle(vid)
    if v:
        st.warning(f"⚠️ **{v['plate']}** 차량을 삭제하시겠습니까? 관련 정비·위치 데이터도 함께 삭제됩니다.")
        dc1, dc2 = st.columns(2)
        if dc1.button("✅ 삭제 확인", type="primary"):
            delete_vehicle(vid)
            st.session_state.veh_confirm_del = None
            st.success("삭제되었습니다.")
            st.rerun()
        if dc2.button("취소"):
            st.session_state.veh_confirm_del = None
            st.rerun()

# ── 등록 / 수정 폼 ───────────────────────────────────────────
if st.session_state.veh_show_form:
    edit_id = st.session_state.veh_edit_id
    is_edit = edit_id is not None
    data    = get_vehicle(edit_id) if is_edit else {}

    st.divider()
    st.subheader("✏️ 차량 수정" if is_edit else "➕ 차량 등록")

    with st.form("vehicle_form", clear_on_submit=False):

        # ── 기본 정보 ──────────────────────────────────────
        st.markdown("#### 기본 정보")
        r1c1, r1c2 = st.columns(2)
        purchase_date = r1c1.text_input("구매일",   value=data.get("purchase_date",""))
        reg_date      = r1c2.text_input("등록일",   value=data.get("reg_date",""))

        r2c1, r2c2 = st.columns(2)
        stock_number = r2c1.text_input("스톡넘버", value=data.get("stock_number",""))
        plate        = r2c2.text_input("번호판 *", value=data.get("plate",""))

        r3c1, r3c2, r3c3 = st.columns(3)
        make   = r3c1.text_input("제조사", value=data.get("make",""))
        model  = r3c2.text_input("모델명", value=data.get("model",""))
        driver = r3c3.text_input("담당자", value=data.get("driver",""))

        r4c1, r4c2, r4c3 = st.columns(3)
        year      = r4c1.text_input("연식",  value=str(data.get("year","") or ""))
        color     = r4c2.text_input("색상",  value=data.get("color",""))
        vin       = r4c3.text_input("VIN",   value=data.get("vin",""))

        r5c1, r5c2, r5c3 = st.columns(3)
        fuel_type_idx = FUEL_TYPES.index(data["fuel_type"]) if data.get("fuel_type") in FUEL_TYPES else 0
        status_idx    = STATUS_LIST.index(data["status"])   if data.get("status")    in STATUS_LIST else 0
        fuel_type = r5c1.selectbox("연료",  FUEL_TYPES, index=fuel_type_idx)
        status    = r5c2.selectbox("상태",  STATUS_LIST, index=status_idx)
        mileage   = r5c3.text_input("주행거리 (km)", value=str(data.get("mileage","") or ""))

        # ── 비용 정보 ──────────────────────────────────────
        st.markdown("#### 비용 정보")
        b1c1, b1c2, b1c3 = st.columns(3)
        vehicle_price    = b1c1.text_input("차량가격(원)", value=str(data.get("vehicle_price","") or ""))
        commission       = b1c2.text_input("수수료(원)",   value=str(data.get("commission","") or ""))
        transport_fee    = b1c3.text_input("탁송비(원)",   value=str(data.get("transport_fee","") or ""))

        b2c1, b2c2, b2c3 = st.columns(3)
        fuel_fee         = b2c1.text_input("기름값(원)",   value=str(data.get("fuel_fee","") or ""))
        performance_spec = b2c2.text_input("성능비(원)",   value=str(data.get("performance_spec","") or ""))
        sale_price       = b2c3.text_input("판매가(USD)",  value=str(data.get("sale_price","") or ""))

        repair_cost_val  = data.get("repair_cost", 0) or 0
        st.info(f"🔒 수리비(정비이력 자동합산): **{fmt_won(repair_cost_val)}**")

        # ── 정비 이력 (수정 시만) ──────────────────────────
        if is_edit:
            from utils.db import get_maintenance
            mh = get_maintenance(vehicle_id=edit_id)
            if mh:
                st.markdown("#### 정비 이력")
                for m in mh[:5]:
                    st.caption(
                        f"{m.get('maint_date','')}  |  {m.get('maint_type','')}  |  "
                        f"{m.get('description','')}  |  {fmt_won(m.get('cost',0))}"
                    )

        # ── 판매 정보 ──────────────────────────────────────
        st.markdown("#### 판매 정보")
        s1c1, s1c2 = st.columns(2)
        sale_date   = s1c1.text_input("판매일",   value=data.get("sale_date",""))
        seller_name = s1c2.text_input("판매자명", value=data.get("seller_name",""))

        # ── 구매자 정보 ────────────────────────────────────
        st.markdown("#### 구매자 정보")
        bc1, bc2 = st.columns(2)
        buyer_name  = bc1.text_input("구매자명", value=data.get("buyer_name",""))
        buyer_phone = bc2.text_input("연락처",   value=data.get("buyer_phone",""))
        bc3, bc4 = st.columns(2)
        buyer_email   = bc3.text_input("이메일", value=data.get("buyer_email",""))
        buyer_address = bc4.text_input("주소",   value=data.get("buyer_address",""))
        notes = st.text_area("메모", value=data.get("notes",""), height=80)

        # ── 버튼 ───────────────────────────────────────────
        fc1, fc2 = st.columns(2)
        submitted = fc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
        cancelled = fc2.form_submit_button("✖ 취소",  use_container_width=True)

    if submitted:
        if not plate.strip():
            st.error("번호판은 필수 항목입니다.")
        else:
            save_data = dict(
                plate         = plate.strip(),
                make          = make.strip(),
                model         = model.strip(),
                year          = safe_int(year),
                color         = color.strip(),
                vin           = vin.strip(),
                fuel_type     = fuel_type,
                status        = status,
                driver        = driver.strip(),
                mileage       = safe_int(mileage),
                vehicle_price = safe_int(vehicle_price),
                commission    = safe_int(commission),
                transport_fee = safe_int(transport_fee),
                fuel_fee      = safe_int(fuel_fee),
                sale_price    = safe_int(sale_price),
                stock_number  = stock_number.strip(),
                performance_spec = performance_spec.strip(),
                buyer_name    = buyer_name.strip(),
                buyer_phone   = buyer_phone.strip(),
                buyer_email   = buyer_email.strip(),
                buyer_address = buyer_address.strip(),
                notes         = notes.strip(),
                sale_date     = sale_date.strip(),
                seller_name   = seller_name.strip(),
                purchase_date = purchase_date.strip(),
                reg_date      = reg_date.strip(),
            )
            try:
                if is_edit:
                    update_vehicle(edit_id, save_data)
                    st.success("수정되었습니다.")
                else:
                    insert_vehicle(save_data)
                    st.success("등록되었습니다.")
                st.session_state.veh_show_form = False
                st.session_state.veh_edit_id   = None
                st.rerun()
            except Exception as e:
                if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                    st.error("이미 등록된 번호판입니다.")
                else:
                    st.error(f"저장 실패: {e}")

    if cancelled:
        st.session_state.veh_show_form = False
        st.session_state.veh_edit_id   = None
        st.rerun()
