"""
Section 9 — Knowledge Graph
Nodes + edges stored in the same SQLite DB as the episodic memory store.
DB: ~/.openclaw/memory/section9.db
export_json() is what the brain graph UI reads.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path.home() / ".openclaw" / "memory" / "section9.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS kg_nodes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT    NOT NULL,
            name        TEXT    NOT NULL UNIQUE,
            properties  TEXT    NOT NULL DEFAULT '{}',
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS kg_edges (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id    INTEGER NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
            target_id    INTEGER NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
            relationship TEXT    NOT NULL,
            weight       REAL    NOT NULL DEFAULT 1.0,
            created_at   TEXT    NOT NULL,
            UNIQUE (source_id, target_id, relationship)
        );

        CREATE INDEX IF NOT EXISTS idx_kgn_type   ON kg_nodes (entity_type);
        CREATE INDEX IF NOT EXISTS idx_kge_source ON kg_edges (source_id);
        CREATE INDEX IF NOT EXISTS idx_kge_target ON kg_edges (target_id);
    """)
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    conn = _connect()
    _init_tables(conn)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Node operations
# ---------------------------------------------------------------------------

def add_node(
    entity_type: str,
    name: str,
    properties: Optional[dict[str, Any]] = None,
) -> int:
    """Insert or update a node. Returns node id."""
    conn = _get_conn()
    props = json.dumps(properties or {})
    ts = _now()

    existing = conn.execute("SELECT id FROM kg_nodes WHERE name = ?", (name,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE kg_nodes SET entity_type=?, properties=? WHERE name=?",
            (entity_type, props, name),
        )
        node_id = existing["id"]
    else:
        cursor = conn.execute(
            "INSERT INTO kg_nodes (entity_type, name, properties, created_at) VALUES (?,?,?,?)",
            (entity_type, name, props, ts),
        )
        node_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return node_id


def get_node(name: str) -> Optional[dict]:
    """Fetch a node by name. Returns None if not found."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM kg_nodes WHERE name = ?", (name,)).fetchone()
    conn.close()
    return _node_to_dict(row) if row else None


def get_subgraph(entity_type: str) -> list[dict]:
    """Return all nodes of a given entity_type."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM kg_nodes WHERE entity_type = ?", (entity_type,)
    ).fetchall()
    conn.close()
    return [_node_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Edge operations
# ---------------------------------------------------------------------------

def add_edge(
    source_name: str,
    target_name: str,
    relationship: str,
    weight: float = 1.0,
) -> int:
    """Insert or update a directed edge between two named nodes. Returns edge id."""
    conn = _get_conn()
    ts = _now()

    src = conn.execute("SELECT id FROM kg_nodes WHERE name=?", (source_name,)).fetchone()
    tgt = conn.execute("SELECT id FROM kg_nodes WHERE name=?", (target_name,)).fetchone()
    if not src:
        raise ValueError(f"Source node '{source_name}' not found.")
    if not tgt:
        raise ValueError(f"Target node '{target_name}' not found.")

    existing = conn.execute(
        "SELECT id FROM kg_edges WHERE source_id=? AND target_id=? AND relationship=?",
        (src["id"], tgt["id"], relationship),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE kg_edges SET weight=? WHERE id=?",
            (weight, existing["id"]),
        )
        edge_id = existing["id"]
    else:
        cursor = conn.execute(
            "INSERT INTO kg_edges (source_id, target_id, relationship, weight, created_at) VALUES (?,?,?,?,?)",
            (src["id"], tgt["id"], relationship, weight, ts),
        )
        edge_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return edge_id


def get_neighbors(name: str) -> dict:
    """Return {outgoing: [...], incoming: [...]} neighbor lists for a named node."""
    conn = _get_conn()
    node = conn.execute("SELECT id FROM kg_nodes WHERE name=?", (name,)).fetchone()
    if not node:
        conn.close()
        return {"outgoing": [], "incoming": []}

    nid = node["id"]

    outgoing = conn.execute(
        """
        SELECT n.name AS target, e.relationship, e.weight
        FROM kg_edges e JOIN kg_nodes n ON e.target_id = n.id
        WHERE e.source_id = ?
        """,
        (nid,),
    ).fetchall()

    incoming = conn.execute(
        """
        SELECT n.name AS source, e.relationship, e.weight
        FROM kg_edges e JOIN kg_nodes n ON e.source_id = n.id
        WHERE e.target_id = ?
        """,
        (nid,),
    ).fetchall()

    conn.close()
    return {
        "outgoing": [dict(r) for r in outgoing],
        "incoming": [dict(r) for r in incoming],
    }


# ---------------------------------------------------------------------------
# Export (brain graph UI)
# ---------------------------------------------------------------------------

def export_json() -> dict:
    """
    Return the full graph as { nodes: [...], edges: [...] }.
    This is the format consumed by the brain graph UI.
    """
    conn = _get_conn()

    nodes = [_node_to_dict(r) for r in conn.execute("SELECT * FROM kg_nodes").fetchall()]

    raw_edges = conn.execute(
        """
        SELECT e.id, s.name AS source, t.name AS target,
               e.relationship, e.weight, e.created_at
        FROM kg_edges e
        JOIN kg_nodes s ON e.source_id = s.id
        JOIN kg_nodes t ON e.target_id = t.id
        """
    ).fetchall()
    conn.close()

    edges = [
        {
            "id": r["id"],
            "source": r["source"],
            "target": r["target"],
            "relationship": r["relationship"],
            "weight": r["weight"],
            "created_at": r["created_at"],
        }
        for r in raw_edges
    ]

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["properties"] = json.loads(d["properties"])
    return d


# ---------------------------------------------------------------------------
# Seed baseline graph
# ---------------------------------------------------------------------------

def seed_baseline() -> None:
    """
    Populate the Section 9 baseline knowledge graph.
    Safe to run multiple times — uses upsert logic.
    """
    agent_roles = {
        "major":    {"role": "orchestrator",  "model": "qwen3:8b",  "description": "Command lead. Owns morning brief and cross-agent coordination."},
        "batou":    {"role": "infrastructure", "model": "llama3.1", "description": "Railway, Docker, deployment ops. Keeps the API alive."},
        "togusa":   {"role": "research",       "model": "llama3.1", "description": "Competitive intelligence and market research."},
        "ishikawa": {"role": "data",           "model": "llama3.1", "description": "Analytics, memory queries, knowledge graph maintenance."},
        "saito":    {"role": "precision",      "model": "llama3.1", "description": "Code review, edge cases, critical path analysis."},
        "paz":      {"role": "community",      "model": "llama3.1", "description": "Ohio homesteader outreach, user acquisition, iMessage."},
        "borma":    {"role": "systems",        "model": "llama3.1", "description": "Background tasks, sleep cycle, cron orchestration."},
    }
    for name, props in agent_roles.items():
        add_node("agent", name, props)

    add_node("goal", "Cincinnati", {
        "description": "Win Cincinnati AI Week pitch — June 9, 2026",
        "deadline": "2026-06-09",
        "ask": "Pre-seed funding",
        "status": "active",
    })
    add_node("goal", "$1M ARR", {
        "description": "Hit $1 million annual recurring revenue",
        "path": "20,833 subscribers @ $4/mo avg = $1M ARR; tiers: Seed $4 | Grower $9 | Homestead $19",
        "status": "active",
    })
    add_node("goal", "users", {
        "description": "Acquire first 10 Ohio homesteader users",
        "channel": "Ohio homesteading communities",
        "status": "active",
    })

    add_node("project", "Zen Vision", {
        "description": "Solarpunk AI platform: plant health, solar management, local AI advisor",
        "tagline": "The earth knows how to sustain us. We help you listen.",
        "url": "https://zen-vision-sigma.vercel.app",
        "api_url": "https://zen-vision-production.up.railway.app",
        "status": "api_broken",
    })

    add_node("competitor", "Plantix",        {"users": "100M", "focus": "crop disease detection", "gap": "farmers only, no solar, no local AI"})
    add_node("competitor", "SmartHelio",     {"focus": "solar AI for utility-scale plants", "gap": "not for individuals, no plant health"})
    add_node("competitor", "Tesla Powerwall",{"focus": "home battery + solar management", "gap": "expensive hardware, no plant health, no local AI"})

    add_node("community", "Ohio homesteaders", {
        "size": "18,000+ in Ohio",
        "channel": "local communities and social groups",
        "status": "target_market",
    })

    for name, props in {
        "Railway":  {"role": "API hosting",          "status": "broken"},
        "Vercel":   {"role": "Frontend hosting",     "status": "live"},
        "FastAPI":  {"role": "Python API framework", "port": 8000},
        "Ollama":   {"role": "Local LLM runtime",    "models": ["llama3.1", "mistral", "qwen3:8b"]},
        "OpenClaw": {"role": "AI agent framework",   "version": "v2026.3.13"},
    }.items():
        add_node("tech", name, props)

    add_node("person", "Aspen Laurent", {
        "role": "founder", "location": "Loveland, Ohio", "email": "aspensolenelaurent@gmail.com",
    })

    # Edges
    for agent in agent_roles:
        add_edge(agent, "Zen Vision", "serves", weight=1.0)

    add_edge("major",    "Cincinnati", "owns",      weight=1.0)
    add_edge("major",    "$1M ARR",    "tracks",    weight=0.9)
    add_edge("paz",      "users",      "owns",      weight=1.0)
    add_edge("togusa",   "Cincinnati", "supports",  weight=0.8)
    add_edge("batou",    "Cincinnati", "supports",  weight=0.7)

    for agent in [a for a in agent_roles if a != "major"]:
        add_edge("major", agent, "coordinates", weight=1.0)

    add_edge("borma",    "major",     "briefs",    weight=1.0)
    add_edge("ishikawa", "Zen Vision","monitors",  weight=0.9)

    for t in ["Railway", "FastAPI", "Vercel"]:
        add_edge("batou", t, "maintains", weight=1.0)

    add_edge("saito", "FastAPI",    "reviews", weight=0.8)
    add_edge("saito", "Zen Vision", "audits",  weight=0.8)
    add_edge("paz",   "Ohio homesteaders", "outreach", weight=1.0)
    add_edge("paz",   "users",             "drives",   weight=1.0)

    for c in ["Plantix", "SmartHelio", "Tesla Powerwall"]:
        add_edge("togusa", c, "monitors", weight=0.8)

    for t in ["Railway", "Vercel", "FastAPI", "Ollama", "OpenClaw"]:
        add_edge("Zen Vision", t, "uses", weight=1.0)

    add_edge("Cincinnati", "$1M ARR",    "validates", weight=0.9)
    add_edge("Cincinnati", "users",      "requires",  weight=1.0)
    add_edge("Cincinnati", "Zen Vision", "demos",     weight=1.0)

    add_edge("Aspen Laurent", "Zen Vision",  "founded",  weight=1.0)
    add_edge("Aspen Laurent", "Cincinnati",  "pitching", weight=1.0)
    add_edge("Aspen Laurent", "$1M ARR",     "targets",  weight=1.0)

    for c in ["Plantix", "SmartHelio", "Tesla Powerwall"]:
        add_edge("Zen Vision", c, "differentiates_from", weight=0.7)

    add_edge("Ohio homesteaders", "users",      "converts_to", weight=1.0)
    add_edge("Ohio homesteaders", "Cincinnati", "validates",   weight=0.8)

    print("Baseline knowledge graph seeded.")


if __name__ == "__main__":
    print(f"DB path: {DB_PATH}")
    seed_baseline()
    graph = export_json()
    print(f"Graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")

    major = get_node("major")
    print(f"\nMajor node: {major}")

    neighbors = get_neighbors("major")
    print(f"\nMajor outgoing ({len(neighbors['outgoing'])}):")
    for n in neighbors["outgoing"]:
        print(f"  → {n['target']} [{n['relationship']}]")
    print("\nKnowledge graph OK.")
