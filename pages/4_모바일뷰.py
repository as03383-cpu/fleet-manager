"""
pages/4_모바일뷰.py — 모바일 최적화 차량 목록
- 카드형 레이아웃 (테이블 없음)
- 큰 버튼, 세로 배치
- 핵심 정보만 표시 + 탭으로 상세 확인
"""

import streamlit as st
from utils.db import (
    get_vehicles, get_vehicle, update_vehicle,
    delete_vehicle, get_maintenance
)
from utils.helpers import (
    STATUS_LIST, STATUS_COLORS, MAKES_LIST,
    safe_int, fmt_km_mi, fmt_won, FUEL_TYPES, calc_dealer_margin
)

st.set_page_config(page_title="모바일 뷰", page_icon="📱", layout="centered")

MAKE_OPTIONS = ["(선택하세요)"] + MAKES_LIST + ["✏️ 직접 입력"]

# ── 모바일 최적화 CSS ─────────────────────────────────────────
st.markdown("""
<style>
/* 전체 여백 최소화 */
.main .block-container {
    padding: 0.5rem 0.6rem 2rem 0.6rem !important;
    max-width: 600px !important;
    margin: 0 auto !important;
}

/* 차량 카드 */
.vcard {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.vcard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.vcard-plate {
    font-size: 1.15rem;
    font-weight: bold;
    color: #f1f5f9;
    letter-spacing: 1px;
}
.vcard-badge {
    font-size: 0.75rem;
    font-weight: bold;
    padding: 3px 8px;
    border-radius: 20px;
    background: #0f172a;
}
.vcard-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.82rem;
    padding: 2px 0;
    color: #94a3b8;
}
.vcard-val { color: #e2e8f0; }

/* 비용 패널 */
.cost-panel {
    background: #0f172a;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    padding: 12px;
    margin-top: 8px;
}
.cost-row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    border-bottom: 1px solid #1e293b;
    font-size: 0.82rem;
}
.cost-row:last-child { border-bottom: none; }
.cost-label { color: #94a3b8; }
.cost-value { color: #f1f5f9; }
.cost-total { color: #f59e0b; font-weight: bold; }
.cost-profit-pos { color: #22c55e; font-weight: bold; font-size: 1rem; }
.cost-profit-neg { color: #ef4444; font-weight: bold; font-size: 1rem; }

/* 버튼 크게 */
.stButton > button {
    font-size: 0.9rem !important;
    padding: 0.5rem 0.8rem !important;
    min-height: 2.4rem !important;
    border-radius: 8px !important;
}

/* 검색창 */
.stTextInput input {
    font-size: 1rem !important;
    padding: 0.5rem !important;
}

/* 구분선 여백 */
hr { margin: 0.5rem 0 !important; }

/* 텍스트 */
p, div, span { font-size: 0.85rem; }
h1 { font-size: 1.4rem !important; }
h3 { font-size: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ── 세션 초기화 ───────────────────────────────────────────────
for k, v in [
    ("mv_cost_open",    None),
    ("mv_edit_open",    None),
    ("mv_del_confirm",  None),
    ("mv_page",         0),
]:
    if k not in st.session_state:
        st.session_state[k] = v

PAGE_SIZE = 20   # 모바일은 20건씩

# ── 상단 ─────────────────────────────────────────────────────
st.title("📱 차량 목록")

search = st.text_input("🔍 번호판·제조사·모델 검색", key="mv_search")
status_filter = st.selectbox("상태 필터", ["전체"] + STATUS_LIST, key="mv_status")

all_rows = get_vehicles(search=search, status_filter=status_filter)
total    = len(all_rows)

page       = st.session_state.mv_page
total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
if page >= total_pages:
    page = total_pages - 1
    st.session_state.mv_page = page

page_rows  = all_rows[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

st.caption(f"총 {total}대  |  {page+1}/{total_pages} 페이지")

if total_pages > 1:
    pc1, pc2, pc3 = st.columns([1, 2, 1])
    if pc1.button("◀ 이전", disabled=(page == 0), use_container_width=True):
        st.session_state.mv_page -= 1
        st.rerun()
    pc2.write("")
    if pc3.button("다음 ▶", disabled=(page >= total_pages - 1), use_container_width=True):
        st.session_state.mv_page += 1
        st.rerun()

st.divider()

# ── 차량 카드 루프 ────────────────────────────────────────────
for r in page_rows:
    vid    = r["id"]
    status = r.get("status", "")
    color  = STATUS_COLORS.get(status, "#94a3b8")
    make   = r.get("make", "") or ""
    model  = r.get("model", "") or ""
    year   = r.get("year", "") or ""
    plate  = r.get("plate", "") or "-"
    driver = r.get("driver", "") or "-"
    mileage = fmt_km_mi(r.get("mileage", 0))

    # 카드 헤더
    st.markdown(f"""
<div class="vcard">
  <div class="vcard-header">
    <span class="vcard-plate">🚗 {plate}</span>
    <span class="vcard-badge" style="color:{color};border:1px solid {color}">{status}</span>
  </div>
  <div class="vcard-row"><span>제조사/모델</span><span class="vcard-val">{make} {model}</span></div>
  <div class="vcard-row"><span>연식</span><span class="vcard-val">{year}년</span></div>
  <div class="vcard-row"><span>주행거리</span><span class="vcard-val">{mileage}</span></div>
  <div class="vcard-row"><span>담당자</span><span class="vcard-val">{driver}</span></div>
  <div class="vcard-row"><span>스톡넘버</span><span class="vcard-val">{r.get('stock_number','') or '-'}</span></div>
</div>
""", unsafe_allow_html=True)

    # 액션 버튼
    b1, b2, b3, b4 = st.columns(4)

    # 💰 비용/이윤
    if b1.button("💰", key=f"mv_cost_{vid}", help="비용/이윤", use_container_width=True):
        st.session_state.mv_cost_open = None if st.session_state.mv_cost_open == vid else vid
        st.session_state.mv_edit_open = None

    # ✏️ 수정
    if b2.button("✏️", key=f"mv_edit_{vid}", help="수정", use_container_width=True):
        st.session_state.mv_edit_open = None if st.session_state.mv_edit_open == vid else vid
        st.session_state.mv_cost_open = None

    # 🔄 상태변경
    if b3.button("🔄", key=f"mv_qs_{vid}", help="상태변경", use_container_width=True):
        cur = r.get("status", STATUS_LIST[0])
        idx = STATUS_LIST.index(cur) if cur in STATUS_LIST else 0
        next_idx = (idx + 1) % len(STATUS_LIST)
        update_vehicle(vid, {"status": STATUS_LIST[next_idx]})
        st.rerun()

    # 🗑️ 삭제
    if b4.button("🗑️", key=f"mv_del_{vid}", help="삭제", use_container_width=True):
        st.session_state.mv_del_confirm = vid

    # ── 💰 비용 패널 ───────────────────────────────────────
    if st.session_state.mv_cost_open == vid:
        rate_key = f"mv_rate_{vid}"
        if rate_key not in st.session_state:
            st.session_state[rate_key] = 1350

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

        total_cost = vp + cm + tf + ff + ps + rc + dm
        sale_krw   = sp * rate
        profit     = sale_krw - total_cost
        p_cls      = "cost-profit-pos" if profit >= 0 else "cost-profit-neg"

        st.markdown(f"""
<div class="cost-panel">
  <div class="cost-row"><span class="cost-label">차량가격</span><span class="cost-value">{vp:,}원</span></div>
  <div class="cost-row"><span class="cost-label">수수료</span><span class="cost-value">{cm:,}원</span></div>
  <div class="cost-row"><span class="cost-label">탁송비</span><span class="cost-value">{tf:,}원</span></div>
  <div class="cost-row"><span class="cost-label">기름값</span><span class="cost-value">{ff:,}원</span></div>
  <div class="cost-row"><span class="cost-label">성능비</span><span class="cost-value">{ps:,}원</span></div>
  <div class="cost-row"><span class="cost-label">수리비(자동)</span><span class="cost-value">{rc:,}원</span></div>
  <div class="cost-row"><span class="cost-label">딜러마진(자동)</span><span class="cost-value">{dm:,}원</span></div>
  <div class="cost-row"><span class="cost-total">총 비용</span><span class="cost-total">{total_cost:,}원</span></div>
  <div class="cost-row"><span class="cost-label">판매가 {sp:,}USD × {rate:,}</span><span class="cost-value">{sale_krw:,}원</span></div>
  <div class="cost-row"><span class="cost-label">이윤</span>
    <span class="{p_cls}">{"▲" if profit>=0 else "▼"} {abs(profit):,}원</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── ✏️ 수정 폼 ─────────────────────────────────────────
    if st.session_state.mv_edit_open == vid:
        data     = get_vehicle(vid) or {}
        fk       = f"mef_{vid}"
        rate_key = f"mv_rate_{vid}"
        if rate_key not in st.session_state:
            st.session_state[rate_key] = 1350

        st.markdown("---")
        st.markdown(f"**✏️ {plate} 수정**")

        # 환율 폼 밖 (즉시 반영)
        st.number_input("💱 환율", min_value=100, max_value=9999, step=10, key=rate_key)

        with st.form(f"mv_edit_{vid}", clear_on_submit=False):
            plate_v  = st.text_input("번호판 *", value=data.get("plate",""),     key=f"{fk}_pl")
            stock_v  = st.text_input("스톡넘버", value=data.get("stock_number",""), key=f"{fk}_sn")

            # 제조사 드롭다운
            cur_make = data.get("make","") or ""
            if cur_make in MAKES_LIST:
                make_idx = MAKES_LIST.index(cur_make) + 1
                make_cust_val = ""
            elif cur_make == "":
                make_idx = 0
                make_cust_val = ""
            else:
                make_idx = len(MAKES_LIST) + 1
                make_cust_val = cur_make

            make_sel  = st.selectbox("제조사", MAKE_OPTIONS, index=make_idx, key=f"{fk}_ms")
            make_cust = st.text_input("직접입력", value=make_cust_val,
                                      placeholder="예: Toyota, Ford...", key=f"{fk}_mc")

            model_v  = st.text_input("모델명",  value=data.get("model",""),  key=f"{fk}_mo")
            year_v   = st.text_input("연식",    value=str(data.get("year","") or ""), key=f"{fk}_yr")
            color_v  = st.text_input("색상",    value=data.get("color",""),  key=f"{fk}_cl")
            driver_v = st.text_input("담당자",  value=data.get("driver",""), key=f"{fk}_dr")
            mileage_v = st.text_input("주행거리(km)", value=str(data.get("mileage","") or ""), key=f"{fk}_ml")

            fuel_idx   = FUEL_TYPES.index(data["fuel_type"]) if data.get("fuel_type") in FUEL_TYPES else 0
            status_idx = STATUS_LIST.index(data["status"])   if data.get("status") in STATUS_LIST else 0
            fuel_v   = st.selectbox("연료",  FUEL_TYPES, index=fuel_idx,   key=f"{fk}_ft")
            status_v = st.selectbox("상태",  STATUS_LIST, index=status_idx, key=f"{fk}_st")

            st.markdown("**💰 비용**")
            vp_v  = st.text_input("차량가격(원)",  value=str(data.get("vehicle_price","") or ""),    key=f"{fk}_vp")
            cm_v  = st.text_input("수수료(원)",    value=str(data.get("commission","") or ""),       key=f"{fk}_cm")
            tf_v  = st.text_input("탁송비(원)",    value=str(data.get("transport_fee","") or ""),    key=f"{fk}_tf")
            ff_v  = st.text_input("기름값(원)",    value=str(data.get("fuel_fee","") or ""),         key=f"{fk}_ff")
            ps_v  = st.text_input("성능비(원)",    value=str(data.get("performance_spec","") or ""), key=f"{fk}_ps")
            sp_v  = st.text_input("판매가(USD)",   value=str(data.get("sale_price","") or ""),       key=f"{fk}_sp")

            rc_val = safe_int(data.get("repair_cost", 0))
            st.info(f"🔒 수리비(자동): **{rc_val:,}원**")

            # 이윤 미리보기
            rate_now = st.session_state.get(rate_key, 1350)
            sp_int   = safe_int(sp_v)
            dm_int   = calc_dealer_margin(sp_int)
            tot_int  = safe_int(vp_v) + safe_int(cm_v) + safe_int(tf_v) + safe_int(ff_v) + safe_int(ps_v) + rc_val + dm_int
            sal_int  = sp_int * rate_now
            prf_int  = sal_int - tot_int

            st.info(f"🚗 딜러마진(자동): **{dm_int:,}원**  |  📊 총비용: **{tot_int:,}원**")
            if prf_int >= 0:
                st.success(f"💹 이윤: **+{prf_int:,}원**  (환율 {rate_now:,})")
            else:
                st.error(f"💹 이윤: **{prf_int:,}원**  (환율 {rate_now:,})")

            st.markdown("**🏷️ 판매 정보**")
            sale_date_v   = st.text_input("판매일(YYYY-MM-DD)", value=data.get("sale_date",""),   key=f"{fk}_sd")
            seller_name_v = st.text_input("판매자명",           value=data.get("seller_name",""), key=f"{fk}_sl")
            notes_v       = st.text_area("📝 메모", value=data.get("notes",""), height=80,        key=f"{fk}_nt")

            sc1, sc2 = st.columns(2)
            submitted = sc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
            cancelled = sc2.form_submit_button("✖ 취소", use_container_width=True)

        if submitted:
            if not plate_v.strip():
                st.error("번호판은 필수입니다.")
            else:
                if make_sel == "✏️ 직접 입력":
                    final_make = make_cust.strip()
                elif make_sel != "(선택하세요)":
                    final_make = make_sel
                else:
                    final_make = make_cust.strip()

                update_vehicle(vid, dict(
                    plate=plate_v.strip(), make=final_make,
                    model=model_v.strip(), year=safe_int(year_v),
                    color=color_v.strip(), driver=driver_v.strip(),
                    mileage=safe_int(mileage_v), fuel_type=fuel_v,
                    status=status_v, stock_number=stock_v.strip(),
                    vehicle_price=safe_int(vp_v), commission=safe_int(cm_v),
                    transport_fee=safe_int(tf_v), fuel_fee=safe_int(ff_v),
                    performance_spec=ps_v.strip(), sale_price=safe_int(sp_v),
                    sale_date=sale_date_v.strip(), seller_name=seller_name_v.strip(),
                    notes=notes_v.strip(),
                ))
                st.success("✅ 저장됐어요!")
                st.session_state.mv_edit_open = None
                st.rerun()

        if cancelled:
            st.session_state.mv_edit_open = None
            st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ── 삭제 확인 ────────────────────────────────────────────────
if st.session_state.mv_del_confirm:
    vid = st.session_state.mv_del_confirm
    v   = get_vehicle(vid)
    if v:
        st.warning(f"⚠️ **{v['plate']}** 삭제하시겠어요?")
        dc1, dc2 = st.columns(2)
        if dc1.button("✅ 삭제", type="primary", use_container_width=True):
            delete_vehicle(vid)
            st.session_state.mv_del_confirm = None
            st.success("삭제됐어요.")
            st.rerun()
        if dc2.button("취소", use_container_width=True):
            st.session_state.mv_del_confirm = None
            st.rerun()
