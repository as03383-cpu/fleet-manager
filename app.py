"""
app.py — 대시보드 (메인 페이지)
"""

import streamlit as st
from utils.db import init_db, get_stats, get_recent_vehicles
from utils.helpers import STATUS_COLORS, fmt_won

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="차량관리 시스템",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DB 초기화 (최초 1회) ─────────────────────────────────────
init_db()

# ── 커스텀 CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    /* 사이드바 배경 */
    [data-testid="stSidebar"] { background-color: #1e293b; }
    /* 메트릭 카드 */
    [data-testid="metric-container"] {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 16px;
    }
    /* 버튼 */
    .stButton > button {
        border-radius: 6px;
        border: none;
        font-weight: 600;
    }
    /* 테이블 헤더 */
    [data-testid="stDataFrame"] thead th {
        background-color: #1e293b !important;
        color: #94a3b8 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ─────────────────────────────────────────────────────
st.title("🚗 차량관리 시스템 v2.3")
st.caption("실시간 차량 관리 대시보드")

st.divider()

# ── 통계 카드 ────────────────────────────────────────────────
stats = get_stats() or {}

cols = st.columns(7)
card_data = [
    ("🚗 전체",    stats.get("total",   0), "#3b82f6"),
    ("🔧 정비중",  stats.get("repair",  0), "#f59e0b"),
    ("⏳ 정비대기", stats.get("waiting", 0), "#f97316"),
    ("🧹 세차대기", stats.get("wash",    0), "#a78bfa"),
    ("✅ 판매준비", stats.get("ready",   0), "#22d3ee"),
    ("💰 판매완료", stats.get("sold",    0), "#22c55e"),
    ("🚫 폐차",    stats.get("scrap",   0), "#ef4444"),
]
for col, (label, val, color) in zip(cols, card_data):
    with col:
        st.metric(label=label, value=int(val or 0))

st.divider()

# ── 최근 등록 차량 ───────────────────────────────────────────
st.subheader("최근 등록 차량")

recent = get_recent_vehicles(10)
if recent:
    for v in recent:
        status  = v.get("status","")
        color   = STATUS_COLORS.get(status, "#94a3b8")
        c1, c2, c3 = st.columns([2, 4, 2])
        with c1:
            st.write(f"**{v.get('plate','')}**")
        with c2:
            st.write(f"{v.get('make','')} {v.get('model','')}")
        with c3:
            st.markdown(
                f'<span style="color:{color};font-weight:bold">{status}</span>',
                unsafe_allow_html=True
            )
else:
    st.info("등록된 차량이 없습니다.")

# ── 사이드바 안내 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 메뉴")
    st.markdown("""
- 🚗 **차량 목록** — 차량 등록·수정·삭제
- 🔧 **정비 이력** — 정비 기록 관리
- 📍 **위치 관리** — 위치 기록 조회
""")
    st.divider()
    st.caption("좌측 메뉴에서 페이지를 선택하세요.")
