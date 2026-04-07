"""
pages/1_차량목록.py — 차량 목록 / 등록 / 수정 / 삭제
원본 CarManager_v2.3 기능 완전 반영:
  - 비용 패널 (차량값/수수료/탁송/기름/성능비/수리비/총비용/이윤)
  - USD 환율 적용 이윤 계산
  - 상태별 색상 배지
  - 🔄 빠른 상태 변경 (원본 우클릭 메뉴 대체)
  - 컬럼 헤더 필터 (제조사, 담당자, 연식)
  - 페이지네이션 (100건 단위)
"""

import streamlit as st
from utils.db import (
    get_vehicles, get_vehicle, insert_vehicle,
    update_vehicle, delete_vehicle, get_maintenance
)
from utils.helpers import (
    STATUS_LIST, FUEL_TYPES, STATUS_COLORS,
    safe_int, fmt_km_mi, fmt_won, MOBILE_CSS
)

st.set_page_config(page_title="차량 목록", page_icon="🚗", layout="wide")
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# ── 커스텀 CSS ──────────────────────────────────────────────────
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
.quick-status-box {
    background: #1e293b;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    padding: 10px 16px;
    margin: 4px 0 8px 0;
}
div[data-testid="stHorizontalBlock"] > div { padding: 0 2px; }
</style>
""", unsafe_allow_html=True)

st.title("🚗 차량 목록")

# ── 세션 상태 초기화 ──────────────────────────────────────────
for key, default in [
    ("veh_edit_id",        None),
    ("veh_show_form",      False),
    ("veh_confirm_del",    None),
    ("veh_cost_open",      None),
    ("veh_quick_status",   None),
    ("veh_rate",           1350),
    ("veh_page",           0),
    ("veh_col_filter",     {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

PAGE_SIZE = 100

# ── 검색 / 필터 / 환율 바 ─────────────────────────────────────
c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
with c1:
    search = st.text_input("🔍 검색 (번호판·제조사·모델·스톡넘버)", key="veh_search")
with c2:
    status_filter = st.selectbox("상태 필터", ["전체"] + STATUS_LIST, key="veh_status_filter")
with c3:
    rate = st.number_input("💱 환율(원/USD)", value=st.session_state.veh_rate,
                           min_value=100, max_value=9999, step=10, key="veh_rate_input")
    st.session_state.veh_rate = rate
with c4:
    st.write("")
    st.write("")
    if st.button("➕ 차량 등록", use_container_width=True, type="primary"):
        st.session_state.veh_show_form     = True
        st.session_state.veh_edit_id       = None
        st.session_state.veh_cost_open     = None
        st.session_state.veh_quick_status  = None


# ── 차량 목록 ─────────────────────────────────────────────────
all_rows = get_vehicles(search=search, status_filter=status_filter)

# ── 컬럼 헤더 필터 적용 ──────────────────────────────────────
col_filters = st.session_state.veh_col_filter
FILTER_KEYS = {
    "제조사": "make",
    "담당자": "driver",
    "연식":   "year",
}
filtered_rows = all_rows
for col_label, col_key in FILTER_KEYS.items():
    fval = col_filters.get(col_label)
    if fval and fval != "전체":
        filtered_rows = [r for r in filtered_rows if str(r.get(col_key, "") or "") == fval]

# ── 활성 필터 표시 + 초기화 ──────────────────────────────────
active_filters = {k: v for k, v in col_filters.items() if v and v != "전체"}
if active_filters:
    filter_text = " / ".join(f"{k}={v}" for k, v in active_filters.items())
    fc1, fc2 = st.columns([6, 1])
    fc1.caption(f"🔽 컬럼 필터: {filter_text}")
    if fc2.button("✖ 필터 초기화", use_container_width=True):
        st.session_state.veh_col_filter = {}
        st.session_state.veh_page = 0
        st.rerun()

# 필터용 고유값 추출
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
        new_val = fcols[i].selectbox(
            col_label, options, index=idx, key=f"cfilter_{col_label}"
        )
        if new_val != col_filters.get(col_label):
            st.session_state.veh_col_filter[col_label] = new_val
            st.session_state.veh_page = 0

rows = filtered_rows

if not rows:
    st.info("조건에 맞는 차량이 없습니다.")
else:
    total_count = len(rows)
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    page = st.session_state.veh_page
    if page >= total_pages:
        page = total_pages - 1
        st.session_state.veh_page = page

    start = page * PAGE_SIZE
    end   = min(start + PAGE_SIZE, total_count)
    page_rows = rows[start:end]

    # ── 페이지 네비게이션 (상단) ──
    if total_pages > 1:
        nav1, nav2, nav3 = st.columns([1, 3, 1])
        if nav1.button("◀ 이전", disabled=(page == 0), use_container_width=True, key="prev_top"):
            st.session_state.veh_page = page - 1
            st.rerun()
        nav2.markdown(
            f"<div style='text-align:center;padding:8px;color:#94a3b8'>"
            f"페이지 {page+1}/{total_pages}  (전체 {total_count}대)</div>",
            unsafe_allow_html=True
        )
        if nav3.button("다음 ▶", disabled=(page >= total_pages - 1), use_container_width=True, key="next_top"):
            st.session_state.veh_page = page + 1
            st.rerun()
    else:
        st.caption(f"총 **{total_count}**대")

    # 테이블 헤더
    hcols = st.columns([1.2, 1.5, 1.2, 1, 1.2, 0.8, 2.2, 1.5, 1.3, 1.2, 1.5, 0.7, 0.7, 0.7, 0.7])
    for col, label in zip(hcols, [
        "스톡넘버","번호판","제조사","담당자","모델","연식",
        "주행거리","상태","구매일","판매일","판매자명","💰","✏️","🗑️","🔄"
    ]):
        col.markdown(f'<div class="table-header">{label}</div>', unsafe_allow_html=True)
    st.divider()

    for r in page_rows:
        vid    = r["id"]
        status = r.get("status", "")
        color  = STATUS_COLORS.get(status, "#94a3b8")

        rcols = st.columns([1.2, 1.5, 1.2, 1, 1.2, 0.8, 2.2, 1.5, 1.3, 1.2, 1.5, 0.7, 0.7, 0.7, 0.7])
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

        # ── 빠른 상태변경 폼 (인라인) ──
        if st.session_state.veh_quick_status == vid:
            cur_status = r.get("status", "")
            cur_idx    = STATUS_LIST.index(cur_status) if cur_status in STATUS_LIST else 0
            with st.form(f"qs_form_{vid}"):
                st.markdown(f"**🔄 [{r.get('plate','')}] 상태 변경**")
                new_status = st.selectbox("새 상태", STATUS_LIST, index=cur_idx)
                qc1, qc2   = st.columns(2)
                if qc1.form_submit_button("✅ 변경", type="primary", use_container_width=True):
                    update_vehicle(vid, {"status": new_status})
                    st.session_state.veh_quick_status = None
                    st.rerun()
                if qc2.form_submit_button("✖ 취소", use_container_width=True):
                    st.session_state.veh_quick_status = None

        # ── 비용 패널 ──
        if st.session_state.veh_cost_open == vid:
            full = r
            if full:
                vp   = safe_int(full.get("vehicle_price", 0))
                cm   = safe_int(full.get("commission", 0))
                tf   = safe_int(full.get("transport_fee", 0))
                ff   = safe_int(full.get("fuel_fee", 0))
                ps   = safe_int(full.get("performance_spec", 0))
                rc   = safe_int(full.get("repair_cost", 0))
                sp   = safe_int(full.get("sale_price", 0))

                total    = vp + cm + tf + ff + ps + rc
                sale_krw = sp * rate
                profit   = sale_krw - total
                profit_color = "cost-profit-pos" if profit >= 0 else "cost-profit-neg"

                st.markdown(f"""
<div class="cost-panel">
  <div style="font-size:0.8rem;color:#60a5fa;font-weight:bold;margin-bottom:6px">
    💰 {full.get('plate','')} 비용 분석
  </div>
  <div class="cost-row"><span class="cost-label">차량가격</span><span class="cost-value">{vp:,}원</span></div>
  <div class="cost-row"><span class="cost-label">수수료</span><span class="cost-value">{cm:,}원</span></div>
  <div class="cost-row"><span class="cost-label">탁송비</span><span class="cost-value">{tf:,}원</span></div>
  <div class="cost-row"><span class="cost-label">기름값</span><span class="cost-value">{ff:,}원</span></div>
  <div class="cost-row"><span class="cost-label">성능비</span><span class="cost-value">{ps:,}원</span></div>
  <div class="cost-row"><span class="cost-label">수리비(자동)</span><span class="cost-value">{rc:,}원</span></div>
  <div class="cost-row"><span class="cost-total">총 비용</span><span class="cost-total">{total:,}원</span></div>
  <div class="cost-row"><span class="cost-label">판매가 {sp:,}USD × {rate:,}</span><span class="cost-value">{sale_krw:,}원</span></div>
  <div class="cost-row"><span class="cost-label">이윤</span>
    <span class="{profit_color}">{"▲" if profit>=0 else "▼"} {abs(profit):,}원</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── 페이지 네비게이션 (하단) ──
    if total_pages > 1:
        nav1b, nav2b, nav3b = st.columns([1, 3, 1])
        if nav1b.button("◀ 이전", disabled=(page == 0), use_container_width=True, key="prev_bot"):
            st.session_state.veh_page = page - 1
            st.rerun()
        nav2b.markdown(
            f"<div style='text-align:center;padding:8px;color:#94a3b8'>"
            f"페이지 {page+1}/{total_pages}  (전체 {total_count}대)</div>",
            unsafe_allow_html=True
        )
        if nav3b.button("다음 ▶", disabled=(page >= total_pages - 1), use_container_width=True, key="next_bot"):
            st.session_state.veh_page = page + 1
            st.rerun()

# ── 삭제 확인 ─────────────────────────────────────────────────
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

# ── 등록 / 수정 폼 ────────────────────────────────────────────
if st.session_state.veh_show_form:
    edit_id = st.session_state.veh_edit_id
    is_edit = edit_id is not None
    data    = get_vehicle(edit_id) if is_edit else {}

    st.divider()
    st.subheader("✏️ 차량 수정" if is_edit else "➕ 차량 등록")

    with st.form("vehicle_form", clear_on_submit=False):

        # 기본 정보
        st.markdown("#### 📋 기본 정보")
        r1c1, r1c2 = st.columns(2)
        purchase_date = r1c1.text_input("구매일 (YYYY-MM-DD)", value=data.get("purchase_date", ""))
        stock_number  = r1c2.text_input("스톡넘버",            value=data.get("stock_number", ""))

        r2c1, r2c2, r2c3 = st.columns(3)
        plate  = r2c1.text_input("번호판 *", value=data.get("plate", ""))
        make   = r2c2.text_input("제조사",   value=data.get("make", ""))
        driver = r2c3.text_input("담당자",   value=data.get("driver", ""))

        r3c1, r3c2, r3c3 = st.columns(3)
        model = r3c1.text_input("모델명", value=data.get("model", ""))
        year  = r3c2.text_input("연식",   value=str(data.get("year", "") or ""))
        color = r3c3.text_input("색상",   value=data.get("color", ""))

        r4c1, r4c2, r4c3 = st.columns(3)
        vin = r4c1.text_input("VIN", value=data.get("vin", ""))
        fuel_type_idx = FUEL_TYPES.index(data["fuel_type"]) if data.get("fuel_type") in FUEL_TYPES else 0
        status_idx    = STATUS_LIST.index(data["status"])   if data.get("status")    in STATUS_LIST else 0
        fuel_type = r4c2.selectbox("연료",  FUEL_TYPES, index=fuel_type_idx)
        status    = r4c3.selectbox("상태",  STATUS_LIST, index=status_idx)

        mileage = st.text_input("주행거리 (km)", value=str(data.get("mileage", "") or ""))

        # 비용 정보
        st.markdown("#### 💰 비용 정보")
        b1c1, b1c2, b1c3 = st.columns(3)
        vehicle_price    = b1c1.text_input("차량가격 (원)",  value=str(data.get("vehicle_price", "") or ""))
        commission       = b1c2.text_input("수수료 (원)",    value=str(data.get("commission", "") or ""))
        transport_fee    = b1c3.text_input("탁송비 (원)",    value=str(data.get("transport_fee", "") or ""))

        b2c1, b2c2, b2c3 = st.columns(3)
        fuel_fee         = b2c1.text_input("기름값 (원)",    value=str(data.get("fuel_fee", "") or ""))
        performance_spec = b2c2.text_input("성능비 (원)",    value=str(data.get("performance_spec", "") or ""))
        sale_price_usd   = b2c3.text_input("판매가 (USD)",   value=str(data.get("sale_price", "") or ""))

        repair_cost_val = safe_int(data.get("repair_cost", 0))

        # 실시간 비용 미리보기
        vp_preview = safe_int(vehicle_price)
        cm_preview = safe_int(commission)
        tf_preview = safe_int(transport_fee)
        ff_preview = safe_int(fuel_fee)
        ps_preview = safe_int(performance_spec)
        sp_preview = safe_int(sale_price_usd)
        total_preview  = vp_preview + cm_preview + tf_preview + ff_preview + ps_preview + repair_cost_val
        sale_preview   = sp_preview * st.session_state.veh_rate
        profit_preview = sale_preview - total_preview

        col_info1, col_info2, col_info3 = st.columns(3)
        col_info1.info(f"🔒 수리비(자동): **{repair_cost_val:,}원**")
        col_info2.info(f"📊 총비용: **{total_preview:,}원**")
        if profit_preview >= 0:
            col_info3.success(f"💹 이윤: **+{profit_preview:,}원**")
        else:
            col_info3.error(f"💹 이윤: **{profit_preview:,}원**")

        # 정비 이력 (수정 시)
        if is_edit:
            mh = get_maintenance(vehicle_id=edit_id)
            if mh:
                st.markdown("#### 🔧 최근 정비 이력")
                for m in mh[:5]:
                    st.caption(
                        f"{m.get('maint_date','')}  |  {m.get('maint_type','')}  |  "
                        f"{m.get('description','')}  |  {fmt_won(m.get('cost',0))}"
                    )

        # 판매 정보
        st.markdown("#### 🏷️ 판매 정보")
        s1c1, s1c2 = st.columns(2)
        sale_date   = s1c1.text_input("판매일 (YYYY-MM-DD)", value=data.get("sale_date", ""))
        seller_name = s1c2.text_input("판매자명",            value=data.get("seller_name", ""))

        # 구매자 정보
        st.markdown("#### 👤 구매자 정보")
        bc1, bc2 = st.columns(2)
        buyer_name  = bc1.text_input("구매자명", value=data.get("buyer_name", ""))
        buyer_phone = bc2.text_input("연락처",   value=data.get("buyer_phone", ""))
        bc3, bc4 = st.columns(2)
        buyer_email   = bc3.text_input("이메일", value=data.get("buyer_email", ""))
        buyer_address = bc4.text_input("주소",   value=data.get("buyer_address", ""))

        notes = st.text_area("📝 메모", value=data.get("notes", ""), height=80)

        # 버튼
        fc1, fc2 = st.columns(2)
        submitted = fc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
        cancelled = fc2.form_submit_button("✖ 취소",  use_container_width=True)

    if submitted:
        if not plate.strip():
            st.error("번호판은 필수 항목입니다.")
        else:
            save_data = dict(
                plate            = plate.strip(),
                make             = make.strip(),
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
                if is_edit:
                    update_vehicle(edit_id, save_data)
                    st.success("✅ 수정되었습니다.")
                else:
                    insert_vehicle(save_data)
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
