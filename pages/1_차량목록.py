"""
pages/1_차량목록.py — 차량 목록 / 등록 / 수정 / 삭제
변경사항:
  - 수정 폼: 해당 차량 행 바로 아래 인라인 표시
  - 환율 입력: 상단 바 제거 → 수정 폼 비용정보 이윤 바로 위로 이동
  - 딜러마진 자동계산: 판매가 ≤2500→50만, 2501~3000→70만, 3001+→100만
  - 제조사: 드롭다운(Chevrolet/Renault/KG Mobility/Kia/Hyundai) + 직접입력
  - 컬럼 필터 (제조사/담당자/연식) + 페이지네이션 (100건)
"""

import streamlit as st
from utils.db import (
    get_vehicles, get_vehicle, insert_vehicle,
    update_vehicle, delete_vehicle, get_maintenance
)
from utils.helpers import (
    STATUS_LIST, FUEL_TYPES, STATUS_COLORS, MAKES_LIST,
    safe_int, fmt_km_mi, fmt_won, MOBILE_CSS, calc_dealer_margin
)

MAKE_OPTIONS = ["(선택하세요)"] + MAKES_LIST + ["✏️ 직접 입력"]

st.set_page_config(page_title="차량 목록", page_icon="🚗", layout="wide")
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

st.markdown("""
<style>
.cost-panel {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 4px 0 8px 0;
}
.cost-row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    border-bottom: 1px solid #334155;
    font-size: 0.85rem;
}
.cost-row:last-child { border-bottom: none; }
.cost-label { color: #94a3b8; }
.cost-value { color: #f1f5f9; font-weight: 500; }
.cost-total  { color: #f59e0b; font-weight: bold; font-size: 0.9rem; }
.cost-profit-pos { color: #22c55e; font-weight: bold; font-size: 1rem; }
.cost-profit-neg { color: #ef4444; font-weight: bold; font-size: 1rem; }
.table-header { font-weight: bold; color: #94a3b8; font-size: 0.8rem; }
.inline-form-box {
    background: #0f2133;
    border: 1px solid #3b82f6;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 6px 0 10px 0;
}
div[data-testid="stHorizontalBlock"] > div { padding: 0 2px; }
</style>
""", unsafe_allow_html=True)

st.title("🚗 차량 목록")

# ── 세션 상태 초기화 ─────────────────────────────────────────
for key, default in [
    ("veh_edit_id",       None),
    ("veh_show_form",     False),
    ("veh_confirm_del",   None),
    ("veh_cost_open",     None),
    ("veh_quick_status",  None),
    ("veh_rate",          1350),
    ("veh_page",          0),
    ("veh_col_filter",    {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

PAGE_SIZE = 100

# ── 상단 바 (환율 제거 → 3컬럼) ──────────────────────────────
c1, c2, c3 = st.columns([4, 3, 1])
with c1:
    search = st.text_input("🔍 검색 (번호판·제조사·모델·스톡넘버)", key="veh_search")
with c2:
    status_filter = st.selectbox("상태 필터", ["전체"] + STATUS_LIST, key="veh_status_filter")
with c3:
    st.write("")
    st.write("")
    if st.button("➕ 차량 등록", use_container_width=True, type="primary"):
        st.session_state.veh_show_form    = True
        st.session_state.veh_edit_id      = None
        st.session_state.veh_cost_open    = None
        st.session_state.veh_quick_status = None

# ── 새 차량 등록 폼 (검색바 바로 아래) ──────────────────────
if st.session_state.veh_show_form and st.session_state.veh_edit_id is None:
    fk = "nf"
    st.divider()
    st.subheader("➕ 차량 등록")

    with st.form("veh_new_form", clear_on_submit=False):
        st.markdown("#### 📋 기본 정보")
        n1c1, n1c2 = st.columns(2)
        purchase_date = n1c1.text_input("구매일 (YYYY-MM-DD)", key=f"{fk}_pd")
        stock_number  = n1c2.text_input("스톡넘버",            key=f"{fk}_sn")

        n2c1, n2c2, n2c3 = st.columns(3)
        plate       = n2c1.text_input("번호판 *", key=f"{fk}_pl")
        driver      = n2c3.text_input("담당자",   key=f"{fk}_dr")
        make_sel    = n2c2.selectbox("제조사", MAKE_OPTIONS, index=0, key=f"{fk}_ms")
        make_custom = n2c2.text_input("직접 입력", placeholder="예: Toyota, Ford...", key=f"{fk}_mc")

        n3c1, n3c2, n3c3 = st.columns(3)
        model = n3c1.text_input("모델명", key=f"{fk}_mo")
        year  = n3c2.text_input("연식",   key=f"{fk}_yr")
        color = n3c3.text_input("색상",   key=f"{fk}_cl")

        n4c1, n4c2, n4c3 = st.columns(3)
        vin       = n4c1.text_input("VIN", key=f"{fk}_vi")
        fuel_type = n4c2.selectbox("연료",  FUEL_TYPES, key=f"{fk}_ft")
        status    = n4c3.selectbox("상태",  STATUS_LIST, key=f"{fk}_st")

        mileage = st.text_input("주행거리 (km)", key=f"{fk}_ml")

        st.markdown("#### 💰 비용 정보")
        nb1c1, nb1c2, nb1c3 = st.columns(3)
        vehicle_price    = nb1c1.text_input("차량가격 (원)", key=f"{fk}_vp")
        commission       = nb1c2.text_input("수수료 (원)",   key=f"{fk}_cm")
        transport_fee    = nb1c3.text_input("탁송비 (원)",   key=f"{fk}_tf")

        nb2c1, nb2c2, nb2c3 = st.columns(3)
        fuel_fee         = nb2c1.text_input("기름값 (원)",   key=f"{fk}_ff")
        performance_spec = nb2c2.text_input("성능비 (원)",   key=f"{fk}_ps")
        sale_price_usd   = nb2c3.text_input("판매가 (USD)",  key=f"{fk}_sp")

        rate_val = st.number_input(
            "💱 환율 (원/USD)", value=st.session_state.veh_rate,
            min_value=100, max_value=9999, step=10, key=f"{fk}_rate"
        )

        vp_p = safe_int(vehicle_price); cm_p = safe_int(commission)
        tf_p = safe_int(transport_fee); ff_p = safe_int(fuel_fee)
        sp_p = safe_int(sale_price_usd); dm_p = calc_dealer_margin(sp_p)
        tot_p = vp_p + cm_p + tf_p + ff_p + safe_int(performance_spec) + dm_p
        prf_p = sp_p * rate_val - tot_p

        ni1, ni2, ni3 = st.columns(3)
        ni1.info(f"🚗 딜러마진(자동): **{dm_p:,}원**")
        ni2.info(f"📊 총비용: **{tot_p:,}원**")
        if prf_p >= 0: ni3.success(f"💹 이윤: **+{prf_p:,}원**")
        else:          ni3.error(f"💹 이윤: **{prf_p:,}원**")

        st.markdown("#### 🏷️ 판매 정보")
        ns1, ns2 = st.columns(2)
        sale_date   = ns1.text_input("판매일 (YYYY-MM-DD)", key=f"{fk}_sd")
        seller_name = ns2.text_input("판매자명",            key=f"{fk}_sl")

        st.markdown("#### 👤 구매자 정보")
        nbc1, nbc2 = st.columns(2)
        buyer_name  = nbc1.text_input("구매자명", key=f"{fk}_bn")
        buyer_phone = nbc2.text_input("연락처",   key=f"{fk}_bp")
        nbc3, nbc4 = st.columns(2)
        buyer_email   = nbc3.text_input("이메일", key=f"{fk}_be")
        buyer_address = nbc4.text_input("주소",   key=f"{fk}_ba")
        notes = st.text_area("📝 메모", height=80, key=f"{fk}_nt")

        nfc1, nfc2 = st.columns(2)
        submitted = nfc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
        cancelled = nfc2.form_submit_button("✖ 취소",  use_container_width=True)

    if submitted:
        if not plate.strip():
            st.error("번호판은 필수 항목입니다.")
        else:
            st.session_state.veh_rate = rate_val
            if make_sel == "✏️ 직접 입력":   final_make = make_custom.strip()
            elif make_sel != "(선택하세요)":  final_make = make_sel
            else:                             final_make = make_custom.strip()
            try:
                insert_vehicle(dict(
                    plate=plate.strip(), make=final_make, model=model.strip(),
                    year=safe_int(year), color=color.strip(), vin=vin.strip(),
                    fuel_type=fuel_type, status=status, driver=driver.strip(),
                    mileage=safe_int(mileage), vehicle_price=safe_int(vehicle_price),
                    commission=safe_int(commission), transport_fee=safe_int(transport_fee),
                    fuel_fee=safe_int(fuel_fee), sale_price=safe_int(sale_price_usd),
                    stock_number=stock_number.strip(), performance_spec=performance_spec.strip(),
                    buyer_name=buyer_name.strip(), buyer_phone=buyer_phone.strip(),
                    buyer_email=buyer_email.strip(), buyer_address=buyer_address.strip(),
                    notes=notes.strip(), sale_date=sale_date.strip(),
                    seller_name=seller_name.strip(), purchase_date=purchase_date.strip(),
                ))
                st.success("✅ 등록되었습니다.")
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

    st.divider()

# ── 데이터 가져오기 + 컬럼 필터 ─────────────────────────────
all_rows = get_vehicles(search=search, status_filter=status_filter)

col_filters = st.session_state.veh_col_filter
FILTER_KEYS = {"제조사": "make", "담당자": "driver", "연식": "year"}
filtered_rows = all_rows
for col_label, col_key in FILTER_KEYS.items():
    fval = col_filters.get(col_label)
    if fval and fval != "전체":
        filtered_rows = [r for r in filtered_rows if str(r.get(col_key, "") or "") == fval]

active_filters = {k: v for k, v in col_filters.items() if v and v != "전체"}
if active_filters:
    filter_text = " / ".join(f"{k}={v}" for k, v in active_filters.items())
    fc1, fc2 = st.columns([6, 1])
    fc1.caption(f"🔽 컬럼 필터: {filter_text}")
    if fc2.button("✖ 초기화", use_container_width=True):
        st.session_state.veh_col_filter = {}
        st.session_state.veh_page = 0
        st.rerun()

unique_vals = {}
for col_label, col_key in FILTER_KEYS.items():
    vals = sorted({str(r.get(col_key, "") or "") for r in all_rows if r.get(col_key)})
    unique_vals[col_label] = vals

with st.expander("🔽 컬럼별 필터 (제조사 / 담당자 / 연식)", expanded=False):
    fcols = st.columns(len(FILTER_KEYS))
    for i, (col_label, col_key) in enumerate(FILTER_KEYS.items()):
        options = ["전체"] + unique_vals.get(col_label, [])
        current = col_filters.get(col_label, "전체")
        try:
            idx = options.index(current)
        except ValueError:
            idx = 0
        new_val = fcols[i].selectbox(col_label, options, index=idx, key=f"cfilter_{col_label}")
        if new_val != col_filters.get(col_label):
            st.session_state.veh_col_filter[col_label] = new_val
            st.session_state.veh_page = 0

rows = filtered_rows

# ── 차량 목록 & 인라인 폼 ────────────────────────────────────
if not rows:
    st.info("조건에 맞는 차량이 없습니다.")
else:
    total_count = len(rows)
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    page = st.session_state.veh_page
    if page >= total_pages:
        page = total_pages - 1
        st.session_state.veh_page = page

    start     = page * PAGE_SIZE
    end       = min(start + PAGE_SIZE, total_count)
    page_rows = rows[start:end]

    # 페이지 네비게이션 (상단)
    if total_pages > 1:
        n1, n2, n3 = st.columns([1, 3, 1])
        if n1.button("◀ 이전", disabled=(page == 0), use_container_width=True, key="prev_top"):
            st.session_state.veh_page = page - 1
            st.rerun()
        n2.markdown(
            f"<div style='text-align:center;padding:8px;color:#94a3b8'>"
            f"페이지 {page+1}/{total_pages}  (전체 {total_count}대)</div>",
            unsafe_allow_html=True
        )
        if n3.button("다음 ▶", disabled=(page >= total_pages - 1), use_container_width=True, key="next_top"):
            st.session_state.veh_page = page + 1
            st.rerun()
    else:
        st.caption(f"총 **{total_count}**대")

    # 테이블 헤더
    COL_RATIO = [1.2, 1.5, 1.2, 1, 1.2, 0.8, 2.2, 1.5, 1.3, 1.2, 1.5, 0.7, 0.7, 0.7, 0.7]
    hcols = st.columns(COL_RATIO)
    for col, label in zip(hcols, [
        "스톡넘버","번호판","제조사","담당자","모델","연식",
        "주행거리","상태","구매일","판매일","판매자명","💰","✏️","🗑️","🔄"
    ]):
        col.markdown(f'<div class="table-header">{label}</div>', unsafe_allow_html=True)
    st.divider()

    # ── 행 루프 ──────────────────────────────────────────────
    for r in page_rows:
        vid    = r["id"]
        status = r.get("status", "")
        color  = STATUS_COLORS.get(status, "#94a3b8")

        rcols = st.columns(COL_RATIO)
        rcols[0].write(r.get("stock_number") or "-")
        rcols[1].write(r.get("plate", ""))
        rcols[2].write(r.get("make", "") or "-")
        rcols[3].write(r.get("driver", "") or "-")
        rcols[4].write(r.get("model", "") or "-")
        rcols[5].write(str(r.get("year", "") or "-"))
        rcols[6].write(fmt_km_mi(r.get("mileage", 0)))
        rcols[7].markdown(
            f'<span style="color:{color};font-weight:bold">{status}</span>',
            unsafe_allow_html=True
        )
        rcols[8].write(r.get("purchase_date", "") or "-")
        rcols[9].write(r.get("sale_date", "") or "-")
        rcols[10].write(r.get("seller_name", "") or "-")

        # 💰 비용 패널 토글
        if rcols[11].button(
            "🔼" if st.session_state.veh_cost_open == vid else "💰",
            key=f"cost_{vid}", help="비용/이윤 보기"
        ):
            st.session_state.veh_cost_open    = None if st.session_state.veh_cost_open == vid else vid
            st.session_state.veh_quick_status = None

        # ✏️ 수정
        if rcols[12].button("✏️", key=f"edit_{vid}", help="수정"):
            st.session_state.veh_edit_id      = vid
            st.session_state.veh_show_form    = True
            st.session_state.veh_cost_open    = None
            st.session_state.veh_quick_status = None

        # 🗑️ 삭제
        if rcols[13].button("🗑️", key=f"del_{vid}", help="삭제"):
            st.session_state.veh_confirm_del  = vid
            st.session_state.veh_quick_status = None

        # 🔄 빠른 상태변경 토글
        if rcols[14].button(
            "🔼" if st.session_state.veh_quick_status == vid else "🔄",
            key=f"qs_{vid}", help="상태 빠른 변경"
        ):
            st.session_state.veh_quick_status = None if st.session_state.veh_quick_status == vid else vid
            st.session_state.veh_cost_open    = None

        # ── 빠른 상태변경 폼 (인라인) ──────────────────────
        if st.session_state.veh_quick_status == vid:
            cur_status = r.get("status", "")
            cur_idx    = STATUS_LIST.index(cur_status) if cur_status in STATUS_LIST else 0
            with st.form(f"qs_form_{vid}"):
                st.markdown(f"**🔄 [{r.get('plate','')}] 상태 변경**")
                new_status = st.selectbox("새 상태", STATUS_LIST, index=cur_idx)
                qc1, qc2 = st.columns(2)
                if qc1.form_submit_button("✅ 변경", type="primary", use_container_width=True):
                    update_vehicle(vid, {"status": new_status})
                    st.session_state.veh_quick_status = None
                    st.rerun()
                if qc2.form_submit_button("✖ 취소", use_container_width=True):
                    st.session_state.veh_quick_status = None

        # ── 💰 비용 패널 (인라인) ──────────────────────────
        if st.session_state.veh_cost_open == vid:
            rate_key = f"rate_{vid}"
            if rate_key not in st.session_state:
                st.session_state[rate_key] = 1350

            # 환율 입력 — 폼 밖이므로 즉시 반영
            st.number_input(
                "💱 환율 (원/USD)", min_value=100, max_value=9999, step=10,
                key=rate_key
            )
            rate = st.session_state[rate_key]

            vp = safe_int(r.get("vehicle_price", 0))
            cm = safe_int(r.get("commission", 0))
            tf = safe_int(r.get("transport_fee", 0))
            ff = safe_int(r.get("fuel_fee", 0))
            ps = safe_int(r.get("performance_spec", 0))
            rc = safe_int(r.get("repair_cost", 0))
            sp = safe_int(r.get("sale_price", 0))
            dm = calc_dealer_margin(sp)

            total    = vp + cm + tf + ff + ps + rc + dm
            sale_krw = sp * rate
            profit   = sale_krw - total
            p_cls    = "cost-profit-pos" if profit >= 0 else "cost-profit-neg"

            st.markdown(f"""
<div class="cost-panel">
  <div style="font-size:0.8rem;color:#60a5fa;font-weight:bold;margin-bottom:6px">
    💰 {r.get('plate','')} 비용 분석
  </div>
  <div class="cost-row"><span class="cost-label">차량가격</span><span class="cost-value">{vp:,}원</span></div>
  <div class="cost-row"><span class="cost-label">수수료</span><span class="cost-value">{cm:,}원</span></div>
  <div class="cost-row"><span class="cost-label">탁송비</span><span class="cost-value">{tf:,}원</span></div>
  <div class="cost-row"><span class="cost-label">기름값</span><span class="cost-value">{ff:,}원</span></div>
  <div class="cost-row"><span class="cost-label">성능비</span><span class="cost-value">{ps:,}원</span></div>
  <div class="cost-row"><span class="cost-label">수리비(자동)</span><span class="cost-value">{rc:,}원</span></div>
  <div class="cost-row"><span class="cost-label">딜러마진(자동)</span><span class="cost-value">{dm:,}원</span></div>
  <div class="cost-row"><span class="cost-total">총 비용</span><span class="cost-total">{total:,}원</span></div>
  <div class="cost-row"><span class="cost-label">판매가 {sp:,}USD × {rate:,}</span><span class="cost-value">{sale_krw:,}원</span></div>
  <div class="cost-row"><span class="cost-label">이윤</span>
    <span class="{p_cls}">{"▲" if profit>=0 else "▼"} {abs(profit):,}원</span>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── ✏️ 인라인 수정 폼 ─────────────────────────────
        if st.session_state.veh_show_form and st.session_state.veh_edit_id == vid:
            data = get_vehicle(vid) or {}
            fk       = f"ef_{vid}"   # 폼 위젯 키 접두사
            rate_key = f"rate_{vid}"
            if rate_key not in st.session_state:
                st.session_state[rate_key] = 1350

            st.markdown('<div class="inline-form-box">', unsafe_allow_html=True)
            st.subheader(f"✏️ 차량 수정 — {data.get('plate','')}")

            # 환율 입력 — 폼 밖에서 즉시 반영
            st.number_input(
                "💱 환율 (원/USD)", min_value=100, max_value=9999, step=10,
                key=rate_key
            )

            with st.form(f"veh_edit_form_{vid}", clear_on_submit=False):

                # ── 기본 정보 ──────────────────────────────
                st.markdown("#### 📋 기본 정보")
                i1c1, i1c2 = st.columns(2)
                purchase_date = i1c1.text_input("구매일 (YYYY-MM-DD)", value=data.get("purchase_date",""), key=f"{fk}_pd")
                stock_number  = i1c2.text_input("스톡넘버",            value=data.get("stock_number",""),  key=f"{fk}_sn")

                i2c1, i2c2, i2c3 = st.columns(3)
                plate  = i2c1.text_input("번호판 *", value=data.get("plate",""),  key=f"{fk}_pl")
                driver = i2c3.text_input("담당자",   value=data.get("driver",""), key=f"{fk}_dr")

                # 제조사 드롭다운 + 직접입력
                cur_make = data.get("make","") or ""
                if cur_make in MAKES_LIST:
                    make_idx = MAKES_LIST.index(cur_make) + 1
                    make_custom_val = ""
                elif cur_make == "":
                    make_idx = 0
                    make_custom_val = ""
                else:
                    make_idx = len(MAKES_LIST) + 1  # "✏️ 직접 입력"
                    make_custom_val = cur_make

                make_sel    = i2c2.selectbox("제조사", MAKE_OPTIONS, index=make_idx, key=f"{fk}_ms")
                make_custom = i2c2.text_input("직접 입력", value=make_custom_val,
                                              placeholder="예: Toyota, Ford...", key=f"{fk}_mc")

                i3c1, i3c2, i3c3 = st.columns(3)
                model = i3c1.text_input("모델명", value=data.get("model",""), key=f"{fk}_mo")
                year  = i3c2.text_input("연식",   value=str(data.get("year","") or ""), key=f"{fk}_yr")
                color = i3c3.text_input("색상",   value=data.get("color",""), key=f"{fk}_cl")

                i4c1, i4c2, i4c3 = st.columns(3)
                vin = i4c1.text_input("VIN", value=data.get("vin",""), key=f"{fk}_vi")
                fuel_type_idx = FUEL_TYPES.index(data["fuel_type"]) if data.get("fuel_type") in FUEL_TYPES else 0
                status_idx    = STATUS_LIST.index(data["status"])   if data.get("status") in STATUS_LIST else 0
                fuel_type = i4c2.selectbox("연료",  FUEL_TYPES, index=fuel_type_idx, key=f"{fk}_ft")
                status    = i4c3.selectbox("상태",  STATUS_LIST, index=status_idx,   key=f"{fk}_st")

                mileage = st.text_input("주행거리 (km)", value=str(data.get("mileage","") or ""), key=f"{fk}_ml")

                # ── 비용 정보 ──────────────────────────────
                st.markdown("#### 💰 비용 정보")
                b1c1, b1c2, b1c3 = st.columns(3)
                vehicle_price    = b1c1.text_input("차량가격 (원)",  value=str(data.get("vehicle_price","") or ""),    key=f"{fk}_vp")
                commission       = b1c2.text_input("수수료 (원)",    value=str(data.get("commission","") or ""),       key=f"{fk}_cm")
                transport_fee    = b1c3.text_input("탁송비 (원)",    value=str(data.get("transport_fee","") or ""),    key=f"{fk}_tf")

                b2c1, b2c2, b2c3 = st.columns(3)
                fuel_fee         = b2c1.text_input("기름값 (원)",    value=str(data.get("fuel_fee","") or ""),         key=f"{fk}_ff")
                performance_spec = b2c2.text_input("성능비 (원)",    value=str(data.get("performance_spec","") or ""), key=f"{fk}_ps")
                sale_price_usd   = b2c3.text_input("판매가 (USD)",   value=str(data.get("sale_price","") or ""),       key=f"{fk}_sp")

                repair_cost_val = safe_int(data.get("repair_cost", 0))
                st.info(f"🔒 수리비(정비이력 자동합산): **{repair_cost_val:,}원**")

                # 이윤 미리보기 (환율은 폼 밖 number_input에서 즉시 반영됨)
                rate_now = st.session_state.get(rate_key, 1350)
                vp_p  = safe_int(vehicle_price)
                cm_p  = safe_int(commission)
                tf_p  = safe_int(transport_fee)
                ff_p  = safe_int(fuel_fee)
                ps_p  = safe_int(performance_spec)
                sp_p  = safe_int(sale_price_usd)
                dm_p  = calc_dealer_margin(sp_p)
                tot_p = vp_p + cm_p + tf_p + ff_p + ps_p + repair_cost_val + dm_p
                sal_p = sp_p * rate_now
                prf_p = sal_p - tot_p

                pi1, pi2, pi3, pi4 = st.columns(4)
                pi1.info(f"🚗 딜러마진(자동): **{dm_p:,}원**")
                pi2.info(f"📊 총비용: **{tot_p:,}원**")
                pi4.info(f"💱 환율: **{rate_now:,}원**")
                if prf_p >= 0:
                    pi3.success(f"💹 이윤: **+{prf_p:,}원**")
                else:
                    pi3.error(f"💹 이윤: **{prf_p:,}원**")

                # 정비 이력 (수정 시)
                mh = get_maintenance(vehicle_id=vid)
                if mh:
                    st.markdown("#### 🔧 최근 정비 이력")
                    for m in mh[:5]:
                        st.caption(
                            f"{m.get('maint_date','')}  |  {m.get('maint_type','')}  |  "
                            f"{m.get('description','')}  |  {fmt_won(m.get('cost',0))}"
                        )

                # ── 판매 정보 ──────────────────────────────
                st.markdown("#### 🏷️ 판매 정보")
                s1, s2 = st.columns(2)
                sale_date   = s1.text_input("판매일 (YYYY-MM-DD)", value=data.get("sale_date",""),   key=f"{fk}_sd")
                seller_name = s2.text_input("판매자명",            value=data.get("seller_name",""), key=f"{fk}_sl")

                # ── 구매자 정보 ────────────────────────────
                st.markdown("#### 👤 구매자 정보")
                bc1, bc2 = st.columns(2)
                buyer_name  = bc1.text_input("구매자명", value=data.get("buyer_name",""),    key=f"{fk}_bn")
                buyer_phone = bc2.text_input("연락처",   value=data.get("buyer_phone",""),   key=f"{fk}_bp")
                bc3, bc4 = st.columns(2)
                buyer_email   = bc3.text_input("이메일", value=data.get("buyer_email",""),   key=f"{fk}_be")
                buyer_address = bc4.text_input("주소",   value=data.get("buyer_address",""), key=f"{fk}_ba")
                notes = st.text_area("📝 메모", value=data.get("notes",""), height=80, key=f"{fk}_nt")

                fc1, fc2 = st.columns(2)
                submitted = fc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
                cancelled = fc2.form_submit_button("✖ 취소",  use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True)

            if submitted:
                if not plate.strip():
                    st.error("번호판은 필수 항목입니다.")
                else:
                    # 제조사 결정
                    if make_sel == "✏️ 직접 입력":
                        final_make = make_custom.strip()
                    elif make_sel != "(선택하세요)":
                        final_make = make_sel
                    else:
                        final_make = make_custom.strip()

                    save_data = dict(
                        plate            = plate.strip(),
                        make             = final_make,
                        model            = model.strip(),
                        year             = safe_int(year),
                        color            = color.strip(),
                        vin              = vin.strip(),
                        fuel_type        = fuel_type,
                        status           = status,
                        driver           = driver.strip(),
                        mileage          = safe_int(mileage),
                        vehicle_price    = safe_int(vehicle_price),
                        commission       = safe_int(commission),
                        transport_fee    = safe_int(transport_fee),
                        fuel_fee         = safe_int(fuel_fee),
                        sale_price       = safe_int(sale_price_usd),
                        stock_number     = stock_number.strip(),
                        performance_spec = performance_spec.strip(),
                        buyer_name       = buyer_name.strip(),
                        buyer_phone      = buyer_phone.strip(),
                        buyer_email      = buyer_email.strip(),
                        buyer_address    = buyer_address.strip(),
                        notes            = notes.strip(),
                        sale_date        = sale_date.strip(),
                        seller_name      = seller_name.strip(),
                        purchase_date    = purchase_date.strip(),
                    )
                    try:
                        update_vehicle(vid, save_data)
                        st.success("✅ 수정되었습니다.")
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

    # 페이지 네비게이션 (하단)
    if total_pages > 1:
        n1b, n2b, n3b = st.columns([1, 3, 1])
        if n1b.button("◀ 이전", disabled=(page == 0), use_container_width=True, key="prev_bot"):
            st.session_state.veh_page = page - 1
            st.rerun()
        n2b.markdown(
            f"<div style='text-align:center;padding:8px;color:#94a3b8'>"
            f"페이지 {page+1}/{total_pages}  (전체 {total_count}대)</div>",
            unsafe_allow_html=True
        )
        if n3b.button("다음 ▶", disabled=(page >= total_pages - 1), use_container_width=True, key="next_bot"):
            st.session_state.veh_page = page + 1
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

