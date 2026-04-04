"""
Section 9 — Episodic Memory Store
SQLite-backed event log for all 7 OpenClaw agents.
DB: ~/.openclaw/memory/section9.db
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

DB_PATH = Path.home() / ".openclaw" / "memory" / "section9.db"

GoalTag = Literal["cincinnati", "arr", "users", "ops"]

AGENTS = ["major", "batou", "togusa", "ishikawa", "saito", "paz", "borma"]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id    TEXT    NOT NULL,
            timestamp   TEXT    NOT NULL,
            event_type  TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            entities    TEXT    NOT NULL DEFAULT '[]',
            importance  INTEGER NOT NULL DEFAULT 5 CHECK (importance BETWEEN 0 AND 10),
            goal_tag    TEXT    CHECK (goal_tag IN ('cincinnati', 'arr', 'users', 'ops'))
        );

        CREATE INDEX IF NOT EXISTS idx_memory_agent      ON memory (agent_id);
        CREATE INDEX IF NOT EXISTS idx_memory_goal       ON memory (goal_tag);
        CREATE INDEX IF NOT EXISTS idx_memory_ts         ON memory (timestamp);
        CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory (importance);
    """)
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    conn = _connect()
    _init_tables(conn)
    return conn


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_event(
    agent_id: str,
    event_type: str,
    content: str,
    entities: Optional[list[str]] = None,
    importance: int = 5,
    goal_tag: Optional[GoalTag] = None,
) -> int:
    """Insert an episodic event. Returns the new row id."""
    if agent_id not in AGENTS:
        raise ValueError(f"Unknown agent '{agent_id}'. Must be one of: {AGENTS}")
    if not 0 <= importance <= 10:
        raise ValueError("importance must be 0–10")

    conn = _get_conn()
    ts = datetime.now(timezone.utc).isoformat()
    row = conn.execute(
        """
        INSERT INTO memory (agent_id, timestamp, event_type, content, entities, importance, goal_tag)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (agent_id, ts, event_type, content, json.dumps(entities or []), importance, goal_tag),
    )
    conn.commit()
    conn.close()
    return row.lastrowid


def query_recent(agent_id: str, limit: int = 20) -> list[dict]:
    """Return the most recent `limit` events for an agent."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT * FROM memory
        WHERE agent_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (agent_id, limit),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_by_goal(goal_tag: GoalTag) -> list[dict]:
    """Return all events tagged with a specific goal, newest first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM memory WHERE goal_tag = ? ORDER BY timestamp DESC",
        (goal_tag,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_entities(agent_id: str) -> list[str]:
    """Return a deduplicated list of all entity strings ever logged by an agent."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT entities FROM memory WHERE agent_id = ?",
        (agent_id,),
    ).fetchall()
    conn.close()

    seen: set[str] = set()
    for row in rows:
        for entity in json.loads(row["entities"]):
            seen.add(entity)
    return sorted(seen)


def search(query: str) -> list[dict]:
    """Full-text search across content and event_type (case-insensitive)."""
    conn = _get_conn()
    pattern = f"%{query}%"
    rows = conn.execute(
        """
        SELECT * FROM memory
        WHERE content LIKE ? OR event_type LIKE ?
        ORDER BY importance DESC, timestamp DESC
        """,
        (pattern, pattern),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def delete_below_importance(threshold: int = 4) -> int:
    """Remove all events with importance < threshold. Returns deleted row count."""
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM memory WHERE importance < ?", (threshold,)
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["entities"] = json.loads(d["entities"])
    return d


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"DB path: {DB_PATH}")
    conn = _get_conn()
    print("Tables created successfully.")

    for agent in AGENTS:
        event_id = log_event(
            agent_id=agent,
            event_type="init",
            content=f"{agent} memory initialized.",
            entities=[agent, "section9"],
            importance=3,
            goal_tag="ops",
        )
        print(f"  [{agent}] init event → id={event_id}")

    recent = query_recent("major", limit=5)
    print(f"\nRecent events for major ({len(recent)}):")
    for e in recent:
        print(f"  {e['timestamp']} | {e['event_type']} | {e['content']}")

    ops_events = get_by_goal("ops")
    print(f"\nAll 'ops' events: {len(ops_events)}")

    entities = get_entities("major")
    print(f"\nMajor's entities: {entities}")

    results = search("initialized")
    print(f"\nSearch 'initialized': {len(results)} results")

    print("\nSection 9 memory layer OK.")
    conn.close()
