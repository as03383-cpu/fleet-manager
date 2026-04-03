"""
db.py — 데이터베이스 연결 및 쿼리 모듈
로컬: SQLite  /  배포: Supabase PostgreSQL
연결 문자열은 .streamlit/secrets.toml 의 DATABASE_URL 로 관리
"""

import os
import sqlite3
import streamlit as st
from contextlib import contextmanager

# ── DB 연결 문자열 결정 ─────────────────────────────────────
# secrets.toml에 DATABASE_URL이 있으면 PostgreSQL(Supabase),
# 없으면 로컬 SQLite 사용
def _get_db_url():
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return None

DATABASE_URL = _get_db_url()
USE_POSTGRES = DATABASE_URL is not None and DATABASE_URL.startswith("postgresql")

# ── PostgreSQL 연결 ─────────────────────────────────────────
if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

    @contextmanager
    def get_conn():
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def fetchall(sql, params=()):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def fetchone(sql, params=()):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def execute(sql, params=()):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)

    def executemany(sql, param_list):
        with get_conn() as conn:
            cur = conn.cursor()
            psycopg2.extras.execute_batch(cur, sql, param_list)

    PH = "%s"   # PostgreSQL 플레이스홀더

# ── SQLite 연결 ─────────────────────────────────────────────
else:
    _DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fleet_data.db")

    @contextmanager
    def get_conn():
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def fetchall(sql, params=()):
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def fetchone(sql, params=()):
        with get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def execute(sql, params=()):
        with get_conn() as conn:
            conn.execute(sql, params)

    def executemany(sql, param_list):
        with get_conn() as conn:
            conn.executemany(sql, param_list)

    PH = "?"    # SQLite 플레이스홀더

# ── 테이블 초기화 ────────────────────────────────────────────
def init_db():
    if USE_POSTGRES:
        serial = "SERIAL"
        ts     = "TIMESTAMPTZ DEFAULT NOW()"
    else:
        serial = "INTEGER PRIMARY KEY AUTOINCREMENT"
        ts     = "TEXT DEFAULT CURRENT_TIMESTAMP"

    with get_conn() as conn:
        cur = conn.cursor() if USE_POSTGRES else conn

        def exe(sql):
            if USE_POSTGRES:
                cur.execute(sql)
            else:
                conn.execute(sql)

        exe(f"""CREATE TABLE IF NOT EXISTS vehicles (
            id          {serial if not USE_POSTGRES else 'SERIAL PRIMARY KEY'},
            plate       TEXT NOT NULL,
            make        TEXT, model TEXT, year INTEGER,
            color       TEXT, vin TEXT, fuel_type TEXT,
            status      TEXT DEFAULT '운행중',
            driver      TEXT, notes TEXT,
            created_at  {ts},
            mileage     INTEGER DEFAULT 0,
            stock_number TEXT DEFAULT '',
            performance_spec TEXT DEFAULT '',
            buyer_name  TEXT DEFAULT '',
            buyer_phone TEXT DEFAULT '',
            buyer_email TEXT DEFAULT '',
            buyer_address TEXT DEFAULT '',
            vehicle_price INTEGER DEFAULT 0,
            commission  INTEGER DEFAULT 0,
            transport_fee INTEGER DEFAULT 0,
            fuel_fee    INTEGER DEFAULT 0,
            repair_cost INTEGER DEFAULT 0,
            sale_price  INTEGER DEFAULT 0,
            sale_date   TEXT DEFAULT '',
            seller_name TEXT DEFAULT '',
            purchase_date TEXT DEFAULT '',
            reg_date    TEXT DEFAULT '',
            UNIQUE(plate)
        )""")

        exe(f"""CREATE TABLE IF NOT EXISTS maintenance (
            id          {serial if not USE_POSTGRES else 'SERIAL PRIMARY KEY'},
            vehicle_id  INTEGER REFERENCES vehicles(id),
            maint_date  TEXT, maint_type TEXT, description TEXT,
            cost        INTEGER DEFAULT 0,
            mileage     INTEGER DEFAULT 0,
            shop        TEXT, next_date TEXT, notes TEXT,
            created_at  {ts}
        )""")

        exe(f"""CREATE TABLE IF NOT EXISTS locations (
            id            {serial if not USE_POSTGRES else 'SERIAL PRIMARY KEY'},
            vehicle_id    INTEGER REFERENCES vehicles(id),
            location_name TEXT, address TEXT,
            recorded_at   {ts},
            driver TEXT, notes TEXT
        )""")

        if USE_POSTGRES:
            conn.commit()

# ── 캐시 초기화 헬퍼 ─────────────────────────────────────────
# 데이터 변경(insert/update/delete) 후 호출 → 다음 읽기 시 DB에서 새로 가져옴
def clear_cache():
    st.cache_data.clear()

# ── 차량 쿼리 ────────────────────────────────────────────────
@st.cache_data(ttl=60)  # 60초 캐시 → 같은 조건 재조회 시 DB 쿼리 생략
def get_vehicles(search="", status_filter="전체"):
    where, params = [], []
    if search:
        where.append(f"(plate ILIKE {PH} OR make ILIKE {PH} OR model ILIKE {PH} OR stock_number ILIKE {PH})")
        like = f"%{search}%"
        params += [like, like, like, like]
    if status_filter and status_filter != "전체":
        where.append(f"status = {PH}")
        params.append(status_filter)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""SELECT id, stock_number, plate, make, model, year, mileage,
                     status, driver, purchase_date, reg_date, sale_date, seller_name,
                     vehicle_price, commission, transport_fee, fuel_fee,
                     performance_spec, repair_cost, sale_price
              FROM vehicles {clause} ORDER BY id DESC"""
    return fetchall(sql, params)

def get_vehicle(vehicle_id):
    return fetchone(f"SELECT * FROM vehicles WHERE id={PH}", (vehicle_id,))

def insert_vehicle(data: dict):
    cols = ",".join(data.keys())
    phs  = ",".join([PH] * len(data))
    execute(f"INSERT INTO vehicles ({cols}) VALUES ({phs})", list(data.values()))
    clear_cache()

def update_vehicle(vehicle_id, data: dict):
    sets = ",".join(f"{k}={PH}" for k in data.keys())
    execute(f"UPDATE vehicles SET {sets} WHERE id={PH}",
            list(data.values()) + [vehicle_id])
    clear_cache()

def delete_vehicle(vehicle_id):
    execute(f"DELETE FROM maintenance WHERE vehicle_id={PH}", (vehicle_id,))
    execute(f"DELETE FROM locations   WHERE vehicle_id={PH}", (vehicle_id,))
    execute(f"DELETE FROM vehicles    WHERE id={PH}",         (vehicle_id,))
    clear_cache()

# ── 정비이력 쿼리 ────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_maintenance(vehicle_id=None, search=""):
    where, params = [], []
    if vehicle_id:
        where.append(f"m.vehicle_id={PH}")
        params.append(vehicle_id)
    if search:
        where.append(f"(v.plate ILIKE {PH} OR m.description ILIKE {PH})")
        like = f"%{search}%"
        params += [like, like]
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""SELECT m.id, m.maint_date, v.plate, v.make||' '||v.model AS vehicle,
                     m.maint_type, m.description, m.cost, m.mileage, m.shop, m.next_date
              FROM maintenance m JOIN vehicles v ON m.vehicle_id=v.id
              {clause} ORDER BY m.maint_date DESC"""
    return fetchall(sql, params)

def get_maint_record(maint_id):
    return fetchone(f"SELECT * FROM maintenance WHERE id={PH}", (maint_id,))

def insert_maintenance(data: dict):
    cols = ",".join(data.keys())
    phs  = ",".join([PH] * len(data))
    execute(f"INSERT INTO maintenance ({cols}) VALUES ({phs})", list(data.values()))
    _sync_repair_cost(data["vehicle_id"])
    clear_cache()

def update_maintenance(maint_id, data: dict):
    sets = ",".join(f"{k}={PH}" for k in data.keys())
    execute(f"UPDATE maintenance SET {sets} WHERE id={PH}",
            list(data.values()) + [maint_id])
    vid = fetchone(f"SELECT vehicle_id FROM maintenance WHERE id={PH}", (maint_id,))
    if vid:
        _sync_repair_cost(vid["vehicle_id"])
    clear_cache()

def delete_maintenance(maint_id):
    row = fetchone(f"SELECT vehicle_id FROM maintenance WHERE id={PH}", (maint_id,))
    execute(f"DELETE FROM maintenance WHERE id={PH}", (maint_id,))
    if row:
        _sync_repair_cost(row["vehicle_id"])
    clear_cache()

def _sync_repair_cost(vehicle_id):
    total = fetchone(
        f"SELECT COALESCE(SUM(cost),0) AS t FROM maintenance WHERE vehicle_id={PH}",
        (vehicle_id,)
    )["t"]
    execute(f"UPDATE vehicles SET repair_cost={PH} WHERE id={PH}", (total, vehicle_id))

# ── 위치 쿼리 ────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_locations(vehicle_id=None):
    if vehicle_id:
        sql = f"""SELECT l.id, l.recorded_at, v.plate, l.location_name, l.notes
                  FROM locations l JOIN vehicles v ON l.vehicle_id=v.id
                  WHERE l.vehicle_id={PH} ORDER BY l.recorded_at DESC"""
        return fetchall(sql, (vehicle_id,))
    sql = f"""SELECT l.id, l.recorded_at, v.plate, l.location_name, l.notes
              FROM locations l JOIN vehicles v ON l.vehicle_id=v.id
              ORDER BY l.recorded_at DESC"""
    return fetchall(sql)

def insert_location(data: dict):
    cols = ",".join(data.keys())
    phs  = ",".join([PH] * len(data))
    execute(f"INSERT INTO locations ({cols}) VALUES ({phs})", list(data.values()))
    clear_cache()

def delete_location(loc_id):
    execute(f"DELETE FROM locations WHERE id={PH}", (loc_id,))
    clear_cache()

# ── 대시보드 통계 ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_stats():
    return fetchone("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status='정비중'       THEN 1 ELSE 0 END) AS repair,
               SUM(CASE WHEN status='정비대기'     THEN 1 ELSE 0 END) AS waiting,
               SUM(CASE WHEN status='세차대기'     THEN 1 ELSE 0 END) AS wash,
               SUM(CASE WHEN status='판매준비완료' THEN 1 ELSE 0 END) AS ready,
               SUM(CASE WHEN status='판매완료'     THEN 1 ELSE 0 END) AS sold,
               SUM(CASE WHEN status IN ('폐차대기','폐차') THEN 1 ELSE 0 END) AS scrap
        FROM vehicles
    """)

@st.cache_data(ttl=60)
def get_recent_vehicles(limit=7):
    return fetchall(
        f"SELECT plate, make, model, status FROM vehicles ORDER BY id DESC LIMIT {PH}",
        (limit,)
    )

@st.cache_data(ttl=60)
def get_all_vehicles_simple():
    return fetchall("SELECT id, plate, make, model FROM vehicles ORDER BY plate")
