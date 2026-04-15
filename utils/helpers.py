"""helpers.py — 공통 상수 및 유틸리티"""

STATUS_LIST = ["정비중","정비대기","세차대기","판매준비완료","판매완료","폐차대기","폐차"]
FUEL_TYPES  = ["가솔린","디젤","LPG","하이브리드","전기","수소"]
KM_TO_MI    = 0.621371

STATUS_COLORS = {
    "운행중":      "#22c55e",
    "정비중":      "#f59e0b",
    "정비대기":    "#f97316",
    "세차대기":    "#a78bfa",
    "판매준비완료":"#22d3ee",
    "판매완료":    "#3b82f6",
    "폐차대기":    "#f87171",
    "폐차":        "#6b7280",
}

MAINT_TYPES = ["수리","세차","기타"]

def safe_int(v, default=0):
    try:
        val = int(float(str(v).replace(",","").strip()))
        return default if (val < 0 or val > 2_000_000_000) else val
    except Exception:
        return default

def fmt_won(n):
    try:
        return f"{int(n):,}원"
    except Exception:
        return "-"

def fmt_km_mi(km):
    try:
        km = int(km)
        if km == 0:
            return "-"
        return f"{km:,}km / {km * KM_TO_MI:,.0f}mi"
    except Exception:
        return "-"

MAKES_LIST = ["Chevrolet", "Renault", "KG Mobility", "Kia", "Hyundai"]

def calc_dealer_margin(sale_price_usd) -> int:
    """딜러마진 자동계산: 판매가(USD) 구간별 고정 마진"""
    sp = safe_int(sale_price_usd)
    if sp == 0:
        return 0
    elif sp <= 2500:
        return 500_000
    elif sp <= 3000:
        return 700_000
    else:
        return 1_000_000

def status_badge(status: str) -> str:
    """Streamlit markdown용 색상 뱃지 HTML"""
    color = STATUS_COLORS.get(status, "#94a3b8")
    return f'<span style="color:{color};font-weight:bold">{status}</span>'

# ── 모바일 반응형 CSS ─────────────────────────────────────────
MOBILE_CSS = """
<style>
/* ── 모바일 반응형 (768px 이하) ── */
@media screen and (max-width: 768px) {
    /* 여백 축소 */
    .main .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
        padding-top: 0.8rem !important;
        max-width: 100% !important;
    }

    /* 텍스트 크기 */
    p, div, span, li, td, th { font-size: 0.77rem !important; }
    h1 { font-size: 1.25rem !important; }
    h2 { font-size: 1.05rem !important; }
    h3 { font-size: 0.9rem !important; }

    /* 버튼 */
    .stButton > button {
        font-size: 0.72rem !important;
        padding: 0.2rem 0.4rem !important;
        min-height: 1.8rem !important;
    }

    /* 테이블 행 가로 스크롤 */
    [data-testid="stHorizontalBlock"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        flex-wrap: nowrap !important;
    }
    [data-testid="column"] {
        min-width: 52px !important;
        flex-shrink: 0 !important;
    }

    /* 입력 필드 */
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea { font-size: 0.8rem !important; }

    /* 메트릭 카드 */
    [data-testid="metric-container"] {
        padding: 5px 7px !important;
        min-width: 65px !important;
    }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.6rem !important; }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        min-width: 200px !important;
        max-width: 240px !important;
    }

    /* divider 여백 */
    hr { margin: 0.4rem 0 !important; }

    /* caption */
    .stCaption { font-size: 0.72rem !important; }
}
</style>
"""
