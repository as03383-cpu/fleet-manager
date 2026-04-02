"""helpers.py — 공통 상수 및 유틸리티"""

STATUS_LIST = ["운행중","정비중","정비대기","세차대기","판매준비완료","판매완료","폐차대기","폐차"]
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

MAINT_TYPES = ["엔진오일","브레이크","타이어","세차","점검","기타"]

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

def status_badge(status: str) -> str:
    """Streamlit markdown용 색상 뱃지 HTML"""
    color = STATUS_COLORS.get(status, "#94a3b8")
    return f'<span style="color:{color};font-weight:bold">{status}</span>'
