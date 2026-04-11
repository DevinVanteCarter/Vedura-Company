import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "vedura.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS plants (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                variety     TEXT,
                bed         TEXT,
                notes       TEXT,
                planted_at  TEXT NOT NULL,
                expected_harvest_at TEXT,
                status      TEXT DEFAULT 'growing',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scans (
                id          TEXT PRIMARY KEY,
                plant_id    TEXT NOT NULL REFERENCES plants(id),
                health_score INTEGER NOT NULL,
                alerts      TEXT,
                raw         TEXT,
                scanned_at  TEXT NOT NULL,
                synced      INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS harvests (
                id          TEXT PRIMARY KEY,
                plant_id    TEXT NOT NULL REFERENCES plants(id),
                kg          REAL NOT NULL,
                notes       TEXT,
                harvested_at TEXT NOT NULL,
                broadcast   INTEGER DEFAULT 1,
                synced      INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS solar_log (
                id          TEXT PRIMARY KEY,
                solar_kw    REAL,
                battery_pct REAL,
                load_kw     REAL,
                logged_at   TEXT NOT NULL,
                synced      INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS node (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                lat         REAL,
                lon         REAL,
                location    TEXT,
                created_at  TEXT NOT NULL
            );
        """)


# ── PLANTS ──────────────────────────────────────────────

def create_plant(name, variety=None, bed=None, notes=None,
                 planted_at=None, expected_harvest_at=None):
    plant_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    planted_at = planted_at or now
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO plants
            (id, name, variety, bed, notes, planted_at, expected_harvest_at, status, created_at)
            VALUES (?,?,?,?,?,?,?,'growing',?)
        """, (plant_id, name, variety, bed, notes, planted_at, expected_harvest_at, now))
    return get_plant(plant_id)


def get_plant(plant_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM plants WHERE id=?", (plant_id,)).fetchone()
        return dict(row) if row else None


def list_plants():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM plants WHERE status != 'archived' ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_plant_status(plant_id, status):
    with get_conn() as conn:
        conn.execute("UPDATE plants SET status=? WHERE id=?", (status, plant_id))


# ── SCANS ────────────────────────────────────────────────

def save_scan(plant_id, health_score, alerts=None, raw=None):
    scan_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO scans (id, plant_id, health_score, alerts, raw, scanned_at)
            VALUES (?,?,?,?,?,?)
        """, (scan_id, plant_id, health_score,
              json.dumps(alerts or []), json.dumps(raw or {}), now))
    return get_scan(scan_id)


def get_scan(scan_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d['alerts'] = json.loads(d['alerts'] or '[]')
        d['raw'] = json.loads(d['raw'] or '{}')
        return d


def get_scans_for_plant(plant_id, limit=20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM scans WHERE plant_id=? ORDER BY scanned_at DESC LIMIT ?",
            (plant_id, limit)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d['alerts'] = json.loads(d['alerts'] or '[]')
            result.append(d)
        return result


def get_latest_scan(plant_id):
    rows = get_scans_for_plant(plant_id, limit=1)
    return rows[0] if rows else None


# ── HARVESTS ─────────────────────────────────────────────

def log_harvest(plant_id, kg, notes=None, broadcast=True, harvested_at=None):
    harvest_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    harvested_at = harvested_at or now
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO harvests (id, plant_id, kg, notes, harvested_at, broadcast)
            VALUES (?,?,?,?,?,?)
        """, (harvest_id, plant_id, kg, notes, harvested_at, int(broadcast)))
    return get_harvest(harvest_id)


def get_harvest(harvest_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM harvests WHERE id=?", (harvest_id,)).fetchone()
        return dict(row) if row else None


def get_harvests_for_plant(plant_id, limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM harvests WHERE plant_id=? ORDER BY harvested_at DESC LIMIT ?",
            (plant_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_harvests(limit=50):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT h.*, p.name as plant_name, p.variety
            FROM harvests h
            JOIN plants p ON h.plant_id = p.id
            ORDER BY h.harvested_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_harvest_totals():
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as entry_count,
                ROUND(SUM(kg), 2) as total_kg,
                COUNT(DISTINCT plant_id) as crop_count,
                SUM(CASE WHEN broadcast=1 THEN 1 ELSE 0 END) as shared_count
            FROM harvests
        """).fetchone()
        return dict(row) if row else {}


# ── SOLAR LOG ────────────────────────────────────────────

def log_solar(solar_kw, battery_pct, load_kw=None):
    log_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO solar_log (id, solar_kw, battery_pct, load_kw, logged_at)
            VALUES (?,?,?,?,?)
        """, (log_id, solar_kw, battery_pct, load_kw, now))
    return log_id


def get_solar_history(hours=24):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM solar_log
            WHERE logged_at >= datetime('now', ? || ' hours')
            ORDER BY logged_at ASC
        """, (f'-{hours}',)).fetchall()
        return [dict(r) for r in rows]


# ── PLANT TIMELINE ───────────────────────────────────────

def get_plant_timeline(plant_id):
    """Full chronological history of scans + harvests for one plant."""
    plant = get_plant(plant_id)
    if not plant:
        return None

    scans = get_scans_for_plant(plant_id, limit=100)
    harvests = get_harvests_for_plant(plant_id, limit=100)

    events = []
    for s in scans:
        events.append({
            "type": "scan",
            "date": s['scanned_at'],
            "health_score": s['health_score'],
            "alerts": s['alerts'],
        })
    for h in harvests:
        events.append({
            "type": "harvest",
            "date": h['harvested_at'],
            "kg": h['kg'],
            "notes": h['notes'],
        })

    events.sort(key=lambda e: e['date'], reverse=True)

    # Health trend
    scan_scores = [s['health_score'] for s in scans[:5]]
    trend = "stable"
    if len(scan_scores) >= 2:
        if scan_scores[0] > scan_scores[-1] + 4:
            trend = "improving"
        elif scan_scores[0] < scan_scores[-1] - 4:
            trend = "declining"

    return {
        "plant": plant,
        "events": events,
        "latest_score": scan_scores[0] if scan_scores else None,
        "health_trend": trend,
        "total_harvest_kg": sum(h['kg'] for h in harvests),
        "harvest_count": len(harvests),
    }


# ── MYCELIUM BROADCAST QUEUE ─────────────────────────────

def get_unsynced(table, limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE synced=0 LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_synced(table, ids):
    if not ids:
        return
    placeholders = ','.join('?' * len(ids))
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {table} SET synced=1 WHERE id IN ({placeholders})", ids
        )


# ── NODE IDENTITY ────────────────────────────────────────

def get_or_create_node(name, lat=None, lon=None, location=None):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM node LIMIT 1").fetchone()
        if row:
            return dict(row)
        node_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        conn.execute("""
            INSERT INTO node (id, name, lat, lon, location, created_at)
            VALUES (?,?,?,?,?,?)
        """, (node_id, name, lat, lon, location, now))
        return get_or_create_node(name, lat, lon, location)


# Init on import
init_db()
