"""
pages/4_설정.py — 앱 설정 및 통계
원본 CarManager_v2.3 SettingsTab 대응:
  - 앱 정보 / DB 통계
  - 데이터 CSV 내보내기
  - 상태 목록 / 정비유형 참고
"""

import streamlit as st
import csv
import io
from utils.db import get_stats, get_vehicles, get_maintenance, get_locations

st.set_page_config(page_title="설정", page_icon="⚙️", layout="wide")

st.title("⚙️ 설정 및 통계")

# ── 앱 정보 ──────────────────────────────────────────────────
st.markdown("### 📋 앱 정보")
col1, col2 = st.columns(2)
with col1:
    st.info("""
**차량관리 시스템 v2.3**

- 개발: CarManager Web Edition
- 데이터베이스: Supabase PostgreSQL
- 프레임워크: Streamlit
""")
with col2:
    stats = get_stats() or {}
    total = int(stats.get("total", 0) or 0)
    st.success(f"""
**데이터베이스 현황**

- 🚗 등록 차량: **{total}대**
- 🔧 정비중: **{int(stats.get('repair', 0) or 0)}대**
- ✅ 판매준비: **{int(stats.get('ready', 0) or 0)}대**
- 💰 판매완료: **{int(stats.get('sold', 0) or 0)}대**
""")

st.divider()

# ── 상태 목록 참고 ────────────────────────────────────────────
st.markdown("### 🚦 차량 상태 목록")
from utils.helpers import STATUS_LIST, STATUS_COLORS, MAINT_TYPES

cols = st.columns(len(STATUS_LIST))
for col, s in zip(cols, STATUS_LIST):
    color = STATUS_COLORS.get(s, "#94a3b8")
    col.markdown(
        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:6px;'
        f'padding:8px;text-align:center;color:{color};font-weight:bold">{s}</div>',
        unsafe_allow_html=True
    )

st.divider()

# ── 정비유형 참고 ────────────────────────────────────────────
st.markdown("### 🔧 정비 유형 목록")
maint_cols = st.columns(len(MAINT_TYPES))
for col, mt in zip(maint_cols, MAINT_TYPES):
    col.markdown(
        f'<div style="background:#1e293b;border:1px solid #334155;border-radius:6px;'
        f'padding:8px;text-align:center;color:#94a3b8">{mt}</div>',
        unsafe_allow_html=True
    )

st.divider()

# ── 데이터 내보내기 ───────────────────────────────────────────
st.markdown("### 📤 데이터 내보내기 (CSV)")

col_a, col_b, col_c = st.columns(3)

# 차량 목록 CSV
with col_a:
    if st.button("🚗 차량 목록 CSV", use_container_width=True):
        rows = get_vehicles()
        if rows:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            st.download_button(
                label="💾 다운로드",
                data=buf.getvalue().encode("utf-8-sig"),
                file_name="차량목록.csv",
                mime="text/csv",
            )
        else:
            st.warning("데이터가 없습니다.")

# 정비이력 CSV
with col_b:
    if st.button("🔧 정비이력 CSV", use_container_width=True):
        rows = get_maintenance()
        if rows:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            st.download_button(
                label="💾 다운로드",
                data=buf.getvalue().encode("utf-8-sig"),
                file_name="정비이력.csv",
                mime="text/csv",
            )
        else:
            st.warning("데이터가 없습니다.")

# 위치기록 CSV
with col_c:
    if st.button("📍 위치기록 CSV", use_container_width=True):
        rows = get_locations()
        if rows:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            st.download_button(
                label="💾 다운로드",
                data=buf.getvalue().encode("utf-8-sig"),
                file_name="위치기록.csv",
                mime="text/csv",
            )
        else:
            st.warning("데이터가 없습니다.")

st.divider()
st.caption("💡 데이터는 Supabase PostgreSQL에 저장됩니다. 정기적으로 CSV로 백업하는 것을 권장합니다.")
