"""
pages/4_모바일뷰.py — 모바일 전용 통합 뷰
탭: 🚗 차량목록 | 🔧 정비이력 | 📍 위치관리
- 카드형 레이아웃, 세로 배치, 큰 버튼
- 환율 즉시 반영, 차량별 개별 환율
"""

import streamlit as st
from utils.db import (
    get_vehicles, get_vehicle, update_vehicle, delete_vehicle,
    get_maintenance, get_maint_record, insert_maintenance,
    update_maintenance, delete_maintenance,
    get_locations, get_location, insert_location,
    update_location, delete_location,
    get_all_vehicles_simple,
)
from utils.helpers import (
    STATUS_LIST, STATUS_COLORS, MAKES_LIST,
    MAINT_TYPES, safe_int, fmt_km_mi, fmt_won,
    FUEL_TYPES, calc_dealer_margin,
)

st.set_page_config(page_title="📱 모바일", page_icon="📱", layout="centered")

def _fmt_kst(ts):
    """UTC 타임스탬프 → 한국 표준시(KST, UTC+9), YYYY-MM-DD HH:MM 형식으로 반환"""
    if not ts:
        return "-"
    try:
        from datetime import datetime, timezone, timedelta
        KST = timezone(timedelta(hours=9))
        dt  = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)[:16]

MAKE_OPTIONS = ["(선택하세요)"] + MAKES_LIST + ["✏️ 직접 입력"]

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
.main .block-container {
    padding: 0.5rem 0.7rem 3rem 0.7rem !important;
    max-width: 560px !important;
    margin: 0 auto !important;
}
.vcard {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 13px 15px;
    margin-bottom: 8px;
}
.mcard {
    background: #1a2744;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 11px 13px;
    margin-bottom: 7px;
}
.lcard {
    background: #1a2a1a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 11px 13px;
    margin-bottom: 7px;
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 7px;
}
.card-plate { font-size: 1.1rem; font-weight: bold; color: #f1f5f9; }
.card-badge {
    font-size: 0.72rem; font-weight: bold;
    padding: 2px 8px; border-radius: 20px; background: #0f172a;
}
.card-row {
    display: flex; justify-content: space-between;
    font-size: 0.8rem; padding: 2px 0; color: #94a3b8;
}
.card-val { color: #e2e8f0; }
.cost-panel {
    background: #0f172a; border: 1px solid #3b82f6;
    border-radius: 8px; padding: 11px; margin-top: 6px;
}
.cost-row {
    display: flex; justify-content: space-between;
    padding: 3px 0; border-bottom: 1px solid #1e293b; font-size: 0.8rem;
}
.cost-row:last-child { border-bottom: none; }
.cost-label { color: #94a3b8; }
.cost-value { color: #f1f5f9; }
.cost-total { color: #f59e0b; font-weight: bold; }
.profit-pos { color: #22c55e; font-weight: bold; font-size: 0.95rem; }
.profit-neg { color: #ef4444; font-weight: bold; font-size: 0.95rem; }
.stButton > button {
    font-size: 0.88rem !important;
    padding: 0.45rem 0.5rem !important;
    min-height: 2.3rem !important;
    border-radius: 8px !important;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.9rem !important;
    padding: 6px 10px !important;
}
hr { margin: 0.4rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── 세션 초기화 ───────────────────────────────────────────────
for k, v in [
    ("mv_cost_open",   None), ("mv_edit_open",    None),
    ("mv_del_vid",     None), ("mv_page",          0),
    ("mm_edit_id",     None), ("mm_show_form",     False),
    ("mm_del_id",      None), ("mm_page",          0),
    ("mm_filter_vid",  None),
    ("ml_edit_id",     None), ("ml_show_form",     False),
    ("ml_del_id",      None), ("ml_page",          0),
    ("ml_filter_vid",  None),
]:
    if k not in st.session_state:
        st.session_state[k] = v

st.title("📱 모바일 뷰")

tab1, tab2, tab3 = st.tabs(["🚗 차량목록", "🔧 정비이력", "📍 위치관리"])

# ══════════════════════════════════════════════════════════════
# TAB 1 — 차량 목록
# ══════════════════════════════════════════════════════════════
with tab1:
    PAGE_V = 20
    search_v = st.text_input("🔍 번호판·제조사·모델", key="mv_search")
    st_filter = st.selectbox("상태", ["전체"] + STATUS_LIST, key="mv_status")

    all_v   = get_vehicles(search=search_v, status_filter=st_filter)
    total_v = len(all_v)
    pg_v    = st.session_state.mv_page
    tp_v    = max(1, (total_v + PAGE_V - 1) // PAGE_V)
    if pg_v >= tp_v:
        pg_v = tp_v - 1
        st.session_state.mv_page = pg_v
    rows_v  = all_v[pg_v * PAGE_V : (pg_v + 1) * PAGE_V]

    st.caption(f"총 {total_v}대  |  {pg_v+1}/{tp_v} 페이지")
    if tp_v > 1:
        pc1, pc2 = st.columns(2)
        if pc1.button("◀ 이전", disabled=(pg_v==0), use_container_width=True, key="vp_prev"):
            st.session_state.mv_page -= 1; st.rerun()
        if pc2.button("다음 ▶", disabled=(pg_v>=tp_v-1), use_container_width=True, key="vp_next"):
            st.session_state.mv_page += 1; st.rerun()

    st.divider()

    for r in rows_v:
        vid    = r["id"]
        status = r.get("status","")
        color  = STATUS_COLORS.get(status,"#94a3b8")
        plate  = r.get("plate","") or "-"
        make   = r.get("make","") or ""
        model  = r.get("model","") or ""
        year   = r.get("year","") or ""
        driver = r.get("driver","") or "-"

        st.markdown(f"""
<div class="vcard">
  <div class="card-header">
    <span class="card-plate">🚗 {plate}</span>
    <span class="card-badge" style="color:{color};border:1px solid {color}">{status}</span>
  </div>
  <div class="card-row"><span>제조사/모델</span><span class="card-val">{make} {model}</span></div>
  <div class="card-row"><span>연식</span><span class="card-val">{year}년</span></div>
  <div class="card-row"><span>주행거리</span><span class="card-val">{fmt_km_mi(r.get("mileage",0))}</span></div>
  <div class="card-row"><span>담당자</span><span class="card-val">{driver}</span></div>
  <div class="card-row"><span>스톡넘버</span><span class="card-val">{r.get("stock_number","") or "-"}</span></div>
</div>
""", unsafe_allow_html=True)

        b1, b2, b3, b4 = st.columns(4)
        if b1.button("💰", key=f"mv_cost_{vid}", use_container_width=True):
            st.session_state.mv_cost_open = None if st.session_state.mv_cost_open == vid else vid
            st.session_state.mv_edit_open = None
        if b2.button("✏️", key=f"mv_edit_{vid}", use_container_width=True):
            st.session_state.mv_edit_open = None if st.session_state.mv_edit_open == vid else vid
            st.session_state.mv_cost_open = None
        if b3.button("🔄", key=f"mv_qs_{vid}", use_container_width=True, help="다음 상태로"):
            cur = r.get("status", STATUS_LIST[0])
            idx = STATUS_LIST.index(cur) if cur in STATUS_LIST else 0
            update_vehicle(vid, {"status": STATUS_LIST[(idx+1) % len(STATUS_LIST)]})
            st.rerun()
        if b4.button("🗑️", key=f"mv_del_{vid}", use_container_width=True):
            st.session_state.mv_del_vid = vid

        # 💰 비용 패널
        if st.session_state.mv_cost_open == vid:
            rk = f"mvr_{vid}"
            if rk not in st.session_state:
                st.session_state[rk] = 1350
            st.number_input("💱 환율(원/USD)", min_value=100, max_value=9999, step=10, key=rk)
            rate = st.session_state[rk]

            vp = safe_int(r.get("vehicle_price",0)); cm = safe_int(r.get("commission",0))
            tf = safe_int(r.get("transport_fee",0)); ff = safe_int(r.get("fuel_fee",0))
            ps = safe_int(r.get("performance_spec",0)); rc = safe_int(r.get("repair_cost",0))
            sp = safe_int(r.get("sale_price",0)); dm = calc_dealer_margin(sp)
            tot = vp+cm+tf+ff+ps+rc+dm; sale_krw = sp*rate; profit = sale_krw-tot
            pc = "profit-pos" if profit>=0 else "profit-neg"
            st.markdown(f"""
<div class="cost-panel">
  <div class="cost-row"><span class="cost-label">차량가격</span><span class="cost-value">{vp:,}원</span></div>
  <div class="cost-row"><span class="cost-label">수수료</span><span class="cost-value">{cm:,}원</span></div>
  <div class="cost-row"><span class="cost-label">탁송비</span><span class="cost-value">{tf:,}원</span></div>
  <div class="cost-row"><span class="cost-label">기름값</span><span class="cost-value">{ff:,}원</span></div>
  <div class="cost-row"><span class="cost-label">성능비</span><span class="cost-value">{ps:,}원</span></div>
  <div class="cost-row"><span class="cost-label">수리비(자동)</span><span class="cost-value">{rc:,}원</span></div>
  <div class="cost-row"><span class="cost-label">딜러마진(자동)</span><span class="cost-value">{dm:,}원</span></div>
  <div class="cost-row"><span class="cost-total">총 비용</span><span class="cost-total">{tot:,}원</span></div>
  <div class="cost-row"><span class="cost-label">판매가 {sp:,}USD × {rate:,}</span><span class="cost-value">{sale_krw:,}원</span></div>
  <div class="cost-row"><span class="cost-label">이윤</span>
    <span class="{pc}">{"▲" if profit>=0 else "▼"} {abs(profit):,}원</span></div>
</div>""", unsafe_allow_html=True)

        # ✏️ 수정 폼
        if st.session_state.mv_edit_open == vid:
            data = get_vehicle(vid) or {}
            fk   = f"mvf_{vid}"
            rk   = f"mvr_{vid}"
            if rk not in st.session_state:
                st.session_state[rk] = 1350

            st.markdown("---")
            st.markdown(f"**✏️ {plate} 수정**")
            st.number_input("💱 환율(원/USD)", min_value=100, max_value=9999, step=10, key=rk)

            with st.form(f"mvform_{vid}"):
                plate_v = st.text_input("번호판 *", value=data.get("plate",""), key=f"{fk}_pl")
                stock_v = st.text_input("스톡넘버",  value=data.get("stock_number",""), key=f"{fk}_sn")

                cur_make = data.get("make","") or ""
                if cur_make in MAKES_LIST:
                    mk_idx = MAKES_LIST.index(cur_make)+1; mk_cust = ""
                elif cur_make == "":
                    mk_idx = 0; mk_cust = ""
                else:
                    mk_idx = len(MAKES_LIST)+1; mk_cust = cur_make

                make_sel  = st.selectbox("제조사", MAKE_OPTIONS, index=mk_idx, key=f"{fk}_ms")
                make_cust = st.text_input("직접입력", value=mk_cust, placeholder="예: Toyota", key=f"{fk}_mc")

                model_v  = st.text_input("모델명",  value=data.get("model",""),  key=f"{fk}_mo")
                year_v   = st.text_input("연식",    value=str(data.get("year","") or ""), key=f"{fk}_yr")
                driver_v = st.text_input("담당자",  value=data.get("driver",""), key=f"{fk}_dr")
                mileage_v= st.text_input("주행km",  value=str(data.get("mileage","") or ""), key=f"{fk}_ml")

                fi = FUEL_TYPES.index(data["fuel_type"]) if data.get("fuel_type") in FUEL_TYPES else 0
                si = STATUS_LIST.index(data["status"])   if data.get("status") in STATUS_LIST else 0
                fuel_v   = st.selectbox("연료",  FUEL_TYPES, index=fi, key=f"{fk}_ft")
                status_v = st.selectbox("상태",  STATUS_LIST, index=si, key=f"{fk}_st")

                st.markdown("**💰 비용**")
                vp_v = st.text_input("차량가격(원)",  value=str(data.get("vehicle_price","") or ""), key=f"{fk}_vp")
                cm_v = st.text_input("수수료(원)",    value=str(data.get("commission","") or ""),    key=f"{fk}_cm")
                tf_v = st.text_input("탁송비(원)",    value=str(data.get("transport_fee","") or ""), key=f"{fk}_tf")
                ff_v = st.text_input("기름값(원)",    value=str(data.get("fuel_fee","") or ""),      key=f"{fk}_ff")
                ps_v = st.text_input("성능비(원)",    value=str(data.get("performance_spec","") or ""), key=f"{fk}_ps")
                sp_v = st.text_input("판매가(USD)",   value=str(data.get("sale_price","") or ""),   key=f"{fk}_sp")

                rc_val = safe_int(data.get("repair_cost",0))
                st.info(f"🔒 수리비(자동): **{rc_val:,}원**")

                rate_now = st.session_state.get(rk, 1350)
                sp_i = safe_int(sp_v); dm_i = calc_dealer_margin(sp_i)
                tot_i = safe_int(vp_v)+safe_int(cm_v)+safe_int(tf_v)+safe_int(ff_v)+safe_int(ps_v)+rc_val+dm_i
                prf_i = sp_i*rate_now - tot_i

                st.info(f"🚗 딜러마진: **{dm_i:,}원**  |  📊 총비용: **{tot_i:,}원**")
                if prf_i >= 0:
                    st.success(f"💹 이윤: **+{prf_i:,}원** (환율 {rate_now:,})")
                else:
                    st.error(f"💹 이윤: **{prf_i:,}원** (환율 {rate_now:,})")

                sale_date_v   = st.text_input("판매일(YYYY-MM-DD)", value=data.get("sale_date",""),   key=f"{fk}_sd")
                seller_name_v = st.text_input("판매자명",           value=data.get("seller_name",""), key=f"{fk}_sl")
                notes_v       = st.text_area("📝 메모", value=data.get("notes",""), height=60,        key=f"{fk}_nt")

                sc1, sc2 = st.columns(2)
                sub_v = sc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
                can_v = sc2.form_submit_button("✖ 취소", use_container_width=True)

            if sub_v:
                if not plate_v.strip():
                    st.error("번호판은 필수입니다.")
                else:
                    fm = make_cust.strip() if make_sel=="✏️ 직접 입력" else (make_sel if make_sel!="(선택하세요)" else make_cust.strip())
                    update_vehicle(vid, dict(
                        plate=plate_v.strip(), make=fm, model=model_v.strip(),
                        year=safe_int(year_v), driver=driver_v.strip(),
                        mileage=safe_int(mileage_v), fuel_type=fuel_v, status=status_v,
                        stock_number=stock_v.strip(),
                        vehicle_price=safe_int(vp_v), commission=safe_int(cm_v),
                        transport_fee=safe_int(tf_v), fuel_fee=safe_int(ff_v),
                        performance_spec=ps_v.strip(), sale_price=safe_int(sp_v),
                        sale_date=sale_date_v.strip(), seller_name=seller_name_v.strip(),
                        notes=notes_v.strip(),
                    ))
                    st.success("✅ 저장됐어요!")
                    st.session_state.mv_edit_open = None
                    st.rerun()
            if can_v:
                st.session_state.mv_edit_open = None; st.rerun()

        st.markdown("<div style='height:3px'></div>", unsafe_allow_html=True)

    # 삭제 확인
    if st.session_state.mv_del_vid:
        vid = st.session_state.mv_del_vid
        v   = get_vehicle(vid)
        if v:
            st.warning(f"⚠️ **{v['plate']}** 삭제하시겠어요?")
            dc1, dc2 = st.columns(2)
            if dc1.button("✅ 삭제", type="primary", use_container_width=True, key="mv_del_ok"):
                delete_vehicle(vid)
                st.session_state.mv_del_vid = None
                st.rerun()
            if dc2.button("취소", use_container_width=True, key="mv_del_cancel"):
                st.session_state.mv_del_vid = None; st.rerun()

# ══════════════════════════════════════════════════════════════
# TAB 2 — 정비 이력
# ══════════════════════════════════════════════════════════════
with tab2:
    PAGE_M = 20
    vehicles = get_all_vehicles_simple()

    veh_opts_m = {"전체 보기": None}
    for v in vehicles:
        lbl = f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip()
        veh_opts_m[lbl] = v["id"]

    sel_lbl_m = st.selectbox("차량 선택", list(veh_opts_m.keys()), key="mm_veh_sel")
    new_vid_m = veh_opts_m[sel_lbl_m]
    if new_vid_m != st.session_state.mm_filter_vid:
        st.session_state.mm_filter_vid = new_vid_m
        st.session_state.mm_page = 0

    search_m = st.text_input("🔍 정비내용·번호판 검색", key="mm_search")

    if st.button("➕ 정비 등록", type="primary", use_container_width=True, key="mm_add"):
        currently_new = st.session_state.mm_show_form and st.session_state.mm_edit_id is None
        st.session_state.mm_show_form = not currently_new
        st.session_state.mm_edit_id   = None

    # ── 등록 폼: ➕ 버튼 바로 아래 ────────────────────────────
    if st.session_state.mm_show_form and st.session_state.mm_edit_id is None:
        veh_labels_n = [f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip() for v in vehicles]
        veh_ids_n    = [v["id"] for v in vehicles]
        st.markdown("**➕ 정비 등록**")
        with st.form("mm_form_new"):
            preset_vid = st.session_state.mm_filter_vid
            try:    preset_idx = veh_ids_n.index(preset_vid) if preset_vid else 0
            except: preset_idx = 0
            sel_veh_n   = st.selectbox("차량 *", veh_labels_n, index=preset_idx)
            sel_vid_n   = veh_ids_n[veh_labels_n.index(sel_veh_n)] if veh_labels_n else None
            mdate_n     = st.text_input("정비일자 * (YYYY-MM-DD)", value="")
            mtype_n     = st.selectbox("정비유형", MAINT_TYPES, index=0)
            desc_n      = st.text_input("정비내용", value="")
            cost_n      = st.text_input("비용(원)", value="")
            mile_n      = st.text_input("주행km", value="")
            shop_n      = st.text_input("정비소", value="")
            ndate_n     = st.text_input("다음점검일 (YYYY-MM-DD)", value="")
            notes_n     = st.text_area("메모", value="", height=70)
            ns1, ns2    = st.columns(2)
            sub_n  = ns1.form_submit_button("💾 저장", type="primary", use_container_width=True)
            can_n  = ns2.form_submit_button("✖ 취소", use_container_width=True)
        if sub_n:
            if not mdate_n.strip():
                st.error("정비일자는 필수입니다.")
            elif not sel_vid_n:
                st.error("차량을 선택하세요.")
            else:
                try:
                    insert_maintenance(dict(vehicle_id=sel_vid_n, maint_date=mdate_n.strip(),
                                           maint_type=mtype_n, description=desc_n.strip(),
                                           cost=safe_int(cost_n), mileage=safe_int(mile_n),
                                           shop=shop_n.strip(), next_date=ndate_n.strip(), notes=notes_n.strip()))
                    st.success("✅ 저장됐어요!")
                    st.session_state.mm_show_form = False; st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")
        if can_n:
            st.session_state.mm_show_form = False; st.rerun()

    st.divider()

    all_m   = get_maintenance(vehicle_id=st.session_state.mm_filter_vid, search=search_m)
    total_m = len(all_m)
    pg_m    = st.session_state.mm_page
    tp_m    = max(1, (total_m + PAGE_M - 1) // PAGE_M)
    if pg_m >= tp_m:
        pg_m = tp_m - 1
        st.session_state.mm_page = pg_m

    st.caption(f"총 {total_m}건  |  {pg_m+1}/{tp_m} 페이지")
    if tp_m > 1:
        mc1, mc2 = st.columns(2)
        if mc1.button("◀ 이전", disabled=(pg_m==0), use_container_width=True, key="mm_prev"):
            st.session_state.mm_page -= 1; st.rerun()
        if mc2.button("다음 ▶", disabled=(pg_m>=tp_m-1), use_container_width=True, key="mm_next"):
            st.session_state.mm_page += 1; st.rerun()

    rows_m = all_m[pg_m*PAGE_M:(pg_m+1)*PAGE_M]

    for r in rows_m:
        mid = r["id"]
        st.markdown(f"""
<div class="mcard">
  <div class="card-header">
    <span style="font-weight:bold;color:#93c5fd">🔧 {r.get('plate','')} — {r.get('maint_type','')}</span>
    <span style="font-size:0.78rem;color:#94a3b8">{r.get('maint_date','')}</span>
  </div>
  <div class="card-row"><span>내용</span><span class="card-val">{r.get('description','') or '-'}</span></div>
  <div class="card-row"><span>비용</span><span class="card-val">{fmt_won(r.get('cost',0))}</span></div>
  <div class="card-row"><span>주행km</span><span class="card-val">{r.get('mileage',0):,}km</span></div>
  <div class="card-row"><span>정비소</span><span class="card-val">{r.get('shop','') or '-'}</span></div>
</div>
""", unsafe_allow_html=True)

        mb1, mb2 = st.columns(2)
        if mb1.button("✏️ 수정", key=f"mm_edit_{mid}", use_container_width=True):
            st.session_state.mm_edit_id   = None if st.session_state.mm_edit_id == mid else mid
            st.session_state.mm_show_form = False
        if mb2.button("🗑️ 삭제", key=f"mm_del_{mid}", use_container_width=True):
            st.session_state.mm_del_id = mid

        # ── 수정 폼: 해당 레코드 바로 아래 ──────────────────────
        if st.session_state.mm_edit_id == mid:
            data_m  = get_maint_record(mid) or {}
            veh_labels_e = [f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip() for v in vehicles]
            veh_ids_e    = [v["id"] for v in vehicles]
            st.markdown("**✏️ 정비 수정**")
            with st.form(f"mm_form_{mid}"):
                preset_vid_e = data_m.get("vehicle_id", st.session_state.mm_filter_vid)
                try:    preset_idx_e = veh_ids_e.index(preset_vid_e) if preset_vid_e else 0
                except: preset_idx_e = 0
                sel_veh_e   = st.selectbox("차량 *", veh_labels_e, index=preset_idx_e)
                sel_vid_e   = veh_ids_e[veh_labels_e.index(sel_veh_e)] if veh_labels_e else None
                mdate_e     = st.text_input("정비일자 * (YYYY-MM-DD)", value=data_m.get("maint_date",""))
                mt_idx_e    = MAINT_TYPES.index(data_m["maint_type"]) if data_m.get("maint_type") in MAINT_TYPES else 0
                mtype_e     = st.selectbox("정비유형", MAINT_TYPES, index=mt_idx_e)
                desc_e      = st.text_input("정비내용",  value=data_m.get("description",""))
                cost_e      = st.text_input("비용(원)",  value=str(data_m.get("cost","") or ""))
                mile_e      = st.text_input("주행km",    value=str(data_m.get("mileage","") or ""))
                shop_e      = st.text_input("정비소",    value=data_m.get("shop",""))
                ndate_e     = st.text_input("다음점검일 (YYYY-MM-DD)", value=data_m.get("next_date",""))
                notes_e     = st.text_area("메모", value=data_m.get("notes",""), height=70)
                es1, es2    = st.columns(2)
                sub_e  = es1.form_submit_button("💾 저장", type="primary", use_container_width=True)
                can_e  = es2.form_submit_button("✖ 취소", use_container_width=True)
            if sub_e:
                if not mdate_e.strip():
                    st.error("정비일자는 필수입니다.")
                elif not sel_vid_e:
                    st.error("차량을 선택하세요.")
                else:
                    try:
                        update_maintenance(mid, dict(vehicle_id=sel_vid_e, maint_date=mdate_e.strip(),
                                                     maint_type=mtype_e, description=desc_e.strip(),
                                                     cost=safe_int(cost_e), mileage=safe_int(mile_e),
                                                     shop=shop_e.strip(), next_date=ndate_e.strip(), notes=notes_e.strip()))
                        st.success("✅ 저장됐어요!")
                        st.session_state.mm_edit_id = None; st.rerun()
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
            if can_e:
                st.session_state.mm_edit_id = None; st.rerun()

    # 삭제 확인
    if st.session_state.mm_del_id:
        mid = st.session_state.mm_del_id
        rec = get_maint_record(mid)
        if rec:
            st.warning(f"⚠️ **{rec.get('maint_date','')} {rec.get('maint_type','')}** 삭제하시겠어요?")
            dd1, dd2 = st.columns(2)
            if dd1.button("✅ 삭제", type="primary", use_container_width=True, key="mm_del_ok"):
                delete_maintenance(mid)
                st.session_state.mm_del_id = None; st.rerun()
            if dd2.button("취소", use_container_width=True, key="mm_del_cancel"):
                st.session_state.mm_del_id = None; st.rerun()

# ══════════════════════════════════════════════════════════════
# TAB 3 — 위치 관리
# ══════════════════════════════════════════════════════════════
with tab3:
    PAGE_L = 20
    vehicles_l = get_all_vehicles_simple()

    veh_opts_l = {"전체 보기": None}
    for v in vehicles_l:
        lbl = f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip()
        veh_opts_l[lbl] = v["id"]

    sel_lbl_l = st.selectbox("차량 선택", list(veh_opts_l.keys()), key="ml_veh_sel")
    new_vid_l = veh_opts_l[sel_lbl_l]
    if new_vid_l != st.session_state.ml_filter_vid:
        st.session_state.ml_filter_vid = new_vid_l
        st.session_state.ml_page = 0

    if st.button("➕ 위치 등록", type="primary", use_container_width=True, key="ml_add"):
        currently_new_l = st.session_state.ml_show_form and st.session_state.ml_edit_id is None
        st.session_state.ml_show_form = not currently_new_l
        st.session_state.ml_edit_id   = None

    # ── 등록 폼: ➕ 버튼 바로 아래 ────────────────────────────
    if st.session_state.ml_show_form and st.session_state.ml_edit_id is None:
        veh_labels_ln = [f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip() for v in vehicles_l]
        veh_ids_ln    = [v["id"] for v in vehicles_l]
        st.markdown("**➕ 위치 등록**")
        with st.form("ml_form_new"):
            preset_vid_ln = st.session_state.ml_filter_vid
            try:    preset_idx_ln = veh_ids_ln.index(preset_vid_ln) if preset_vid_ln else 0
            except: preset_idx_ln = 0
            sel_veh_ln    = st.selectbox("차량 *", veh_labels_ln, index=preset_idx_ln)
            sel_vid_ln    = veh_ids_ln[veh_labels_ln.index(sel_veh_ln)] if veh_labels_ln else None
            loc_name_n    = st.text_input("위치명", value="")
            addr_n        = st.text_input("주소",   value="")
            drv_n         = st.text_input("담당자", value="")
            notes_ln      = st.text_area("메모", value="", height=70)
            lns1, lns2    = st.columns(2)
            sub_ln  = lns1.form_submit_button("💾 저장", type="primary", use_container_width=True)
            can_ln  = lns2.form_submit_button("✖ 취소", use_container_width=True)
        if sub_ln:
            if not sel_vid_ln:
                st.error("차량을 선택하세요.")
            else:
                try:
                    insert_location(dict(vehicle_id=sel_vid_ln, location_name=loc_name_n.strip(),
                                         address=addr_n.strip(), driver=drv_n.strip(), notes=notes_ln.strip()))
                    st.success("✅ 저장됐어요!")
                    st.session_state.ml_show_form = False; st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")
        if can_ln:
            st.session_state.ml_show_form = False; st.rerun()

    st.divider()

    all_l   = get_locations(vehicle_id=st.session_state.ml_filter_vid)
    total_l = len(all_l)
    pg_l    = st.session_state.ml_page
    tp_l    = max(1, (total_l + PAGE_L - 1) // PAGE_L)
    if pg_l >= tp_l:
        pg_l = tp_l - 1
        st.session_state.ml_page = pg_l

    st.caption(f"총 {total_l}건  |  {pg_l+1}/{tp_l} 페이지")
    if tp_l > 1:
        lc1, lc2 = st.columns(2)
        if lc1.button("◀ 이전", disabled=(pg_l==0), use_container_width=True, key="ml_prev"):
            st.session_state.ml_page -= 1; st.rerun()
        if lc2.button("다음 ▶", disabled=(pg_l>=tp_l-1), use_container_width=True, key="ml_next"):
            st.session_state.ml_page += 1; st.rerun()

    rows_l = all_l[pg_l*PAGE_L:(pg_l+1)*PAGE_L]

    for r in rows_l:
        lid = r["id"]
        st.markdown(f"""
<div class="lcard">
  <div class="card-header">
    <span style="font-weight:bold;color:#86efac">📍 {r.get('plate','')}</span>
    <span style="font-size:0.78rem;color:#e2e8f0">{_fmt_kst(r.get('recorded_at',''))}</span>
  </div>
  <div class="card-row"><span>위치명</span><span class="card-val">{r.get('location_name','') or '-'}</span></div>
  <div class="card-row"><span>주소</span><span class="card-val">{r.get('address','') or '-'}</span></div>
  <div class="card-row"><span>담당자</span><span class="card-val">{r.get('driver','') or '-'}</span></div>
  <div class="card-row"><span>메모</span><span class="card-val">{r.get('notes','') or '-'}</span></div>
</div>
""", unsafe_allow_html=True)

        lb1, lb2 = st.columns(2)
        if lb1.button("✏️ 수정", key=f"ml_edit_{lid}", use_container_width=True):
            st.session_state.ml_edit_id   = None if st.session_state.ml_edit_id == lid else lid
            st.session_state.ml_show_form = False
        if lb2.button("🗑️ 삭제", key=f"ml_del_{lid}", use_container_width=True):
            st.session_state.ml_del_id = lid

        # ── 수정 폼: 해당 레코드 바로 아래 ──────────────────────
        if st.session_state.ml_edit_id == lid:
            data_le = get_location(lid) or {}
            veh_labels_le = [f"{v['plate']}  {v.get('make','')} {v.get('model','')}".strip() for v in vehicles_l]
            veh_ids_le    = [v["id"] for v in vehicles_l]
            st.markdown("**✏️ 위치 수정**")
            with st.form(f"ml_form_{lid}"):
                preset_vid_le = data_le.get("vehicle_id", st.session_state.ml_filter_vid)
                try:    preset_idx_le = veh_ids_le.index(preset_vid_le) if preset_vid_le else 0
                except: preset_idx_le = 0
                sel_veh_le  = st.selectbox("차량 *", veh_labels_le, index=preset_idx_le)
                sel_vid_le  = veh_ids_le[veh_labels_le.index(sel_veh_le)] if veh_labels_le else None
                loc_name_e  = st.text_input("위치명", value=data_le.get("location_name",""))
                addr_e      = st.text_input("주소",   value=data_le.get("address",""))
                drv_e       = st.text_input("담당자", value=data_le.get("driver",""))
                notes_le    = st.text_area("메모", value=data_le.get("notes",""), height=70)
                les1, les2  = st.columns(2)
                sub_le = les1.form_submit_button("💾 저장", type="primary", use_container_width=True)
                can_le = les2.form_submit_button("✖ 취소", use_container_width=True)
            if sub_le:
                if not sel_vid_le:
                    st.error("차량을 선택하세요.")
                else:
                    try:
                        update_location(lid, dict(vehicle_id=sel_vid_le, location_name=loc_name_e.strip(),
                                                   address=addr_e.strip(), driver=drv_e.strip(), notes=notes_le.strip()))
                        st.success("✅ 저장됐어요!")
                        st.session_state.ml_edit_id = None; st.rerun()
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
            if can_le:
                st.session_state.ml_edit_id = None; st.rerun()

    # 삭제 확인
    if st.session_state.ml_del_id:
        lid = st.session_state.ml_del_id
        st.warning("⚠️ 이 위치 기록을 삭제하시겠어요?")
        ld1, ld2 = st.columns(2)
        if ld1.button("✅ 삭제", type="primary", use_container_width=True, key="ml_del_ok"):
            delete_location(lid)
            st.session_state.ml_del_id = None; st.rerun()
        if ld2.button("취소", use_container_width=True, key="ml_del_cancel"):
            st.session_state.ml_del_id = None; st.rerun()
