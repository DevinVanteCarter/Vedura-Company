import os
import json
import httpx
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from plant_health.image_analyzer import analyze_image
from plant_health.video_analyzer import analyze_video
from plant_health.solar_ai import SolarAIController
import db

# ── APP ──────────────────────────────────────────────────

app = FastAPI(
    title="Vedura · Zen Vision API",
    description="Solarpunk intelligence for off-grid homesteaders.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


# ── MODELS ───────────────────────────────────────────────

class PlantCreate(BaseModel):
    name: str
    variety: Optional[str] = None
    bed: Optional[str] = None
    notes: Optional[str] = None
    planted_at: Optional[str] = None
    expected_harvest_at: Optional[str] = None


class HarvestLog(BaseModel):
    plant_id: str
    kg: float
    notes: Optional[str] = None
    broadcast: bool = True
    harvested_at: Optional[str] = None


class ScanSave(BaseModel):
    plant_id: str
    health_score: int
    alerts: Optional[list] = []
    raw: Optional[dict] = {}


class SolarLogEntry(BaseModel):
    solar_kw: float
    battery_pct: float
    load_kw: Optional[float] = None


class AdvisorRequest(BaseModel):
    message: str
    plant_id: Optional[str] = None
    include_garden_context: bool = True
    include_mycelium_context: bool = False


class NodeSetup(BaseModel):
    name: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    location: Optional[str] = None


# ── HEALTH ───────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "Vedura · Zen Vision API",
        "status": "alive",
        "version": "2.0.0",
        "message": "The earth knows how to sustain us.",
        "build": "2026.04"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ── EXISTING PLANT SCAN ENDPOINTS (preserved) ────────────

@app.post("/plant/analyze/image")
async def analyze_plant_image(
    file: UploadFile = File(...),
    plant_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    contents = await file.read()
    result = analyze_image(contents)

    # NEW: auto-save to timeline if plant_id provided
    if plant_id and result.get("health_score") is not None:
        saved_scan = db.save_scan(
            plant_id=plant_id,
            health_score=result["health_score"],
            alerts=result.get("alerts", []),
            raw=result
        )
        result["scan_id"] = saved_scan["id"]
        result["saved_to_timeline"] = True

        # Queue Mycelium broadcast in background
        if background_tasks and SUPABASE_URL:
            background_tasks.add_task(sync_scan_to_mycelium, saved_scan["id"])
    else:
        result["saved_to_timeline"] = False

    return result


@app.post("/plant/analyze/video")
async def analyze_plant_video(file: UploadFile = File(...)):
    contents = await file.read()
    result = analyze_video(contents)
    return result


# ── GROW TRACKER — PLANTS ────────────────────────────────

@app.post("/plants")
def create_plant(body: PlantCreate):
    plant = db.create_plant(
        name=body.name,
        variety=body.variety,
        bed=body.bed,
        notes=body.notes,
        planted_at=body.planted_at,
        expected_harvest_at=body.expected_harvest_at
    )
    return plant


@app.get("/plants")
def list_plants():
    plants = db.list_plants()
    # Attach latest scan score to each plant
    for p in plants:
        latest = db.get_latest_scan(p["id"])
        p["latest_health_score"] = latest["health_score"] if latest else None
        p["latest_scan_at"] = latest["scanned_at"] if latest else None
        totals = db.get_harvest_totals()
        p["total_harvest_kg"] = totals.get("total_kg", 0)
    return {"plants": plants, "count": len(plants)}


@app.get("/plants/{plant_id}")
def get_plant(plant_id: str):
    plant = db.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    latest = db.get_latest_scan(plant_id)
    plant["latest_health_score"] = latest["health_score"] if latest else None
    return plant


@app.get("/plants/{plant_id}/timeline")
def get_plant_timeline(plant_id: str):
    timeline = db.get_plant_timeline(plant_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Plant not found")
    return timeline


@app.delete("/plants/{plant_id}")
def archive_plant(plant_id: str):
    db.update_plant_status(plant_id, "archived")
    return {"status": "archived", "plant_id": plant_id}


# ── GROW TRACKER — SCANS ─────────────────────────────────

@app.post("/scans")
def save_scan(body: ScanSave, background_tasks: BackgroundTasks):
    plant = db.get_plant(body.plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    scan = db.save_scan(
        plant_id=body.plant_id,
        health_score=body.health_score,
        alerts=body.alerts,
        raw=body.raw
    )
    if SUPABASE_URL:
        background_tasks.add_task(sync_scan_to_mycelium, scan["id"])
    return scan


@app.get("/plants/{plant_id}/scans")
def get_plant_scans(plant_id: str, limit: int = 20):
    scans = db.get_scans_for_plant(plant_id, limit=limit)
    return {"scans": scans, "count": len(scans)}


# ── GROW TRACKER — HARVESTS ──────────────────────────────

@app.post("/harvests")
def log_harvest(body: HarvestLog, background_tasks: BackgroundTasks):
    plant = db.get_plant(body.plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    harvest = db.log_harvest(
        plant_id=body.plant_id,
        kg=body.kg,
        notes=body.notes,
        broadcast=body.broadcast,
        harvested_at=body.harvested_at
    )
    if body.broadcast and SUPABASE_URL:
        background_tasks.add_task(sync_harvest_to_mycelium, harvest["id"])
    return harvest


@app.get("/harvests")
def list_harvests(limit: int = 50):
    harvests = db.get_recent_harvests(limit=limit)
    totals = db.get_harvest_totals()
    return {
        "harvests": harvests,
        "totals": totals
    }


@app.get("/plants/{plant_id}/harvests")
def get_plant_harvests(plant_id: str):
    harvests = db.get_harvests_for_plant(plant_id)
    total_kg = sum(h["kg"] for h in harvests)
    return {
        "harvests": harvests,
        "total_kg": round(total_kg, 2),
        "count": len(harvests)
    }


# ── SOLAR (existing + logging) ───────────────────────────

solar_controller = SolarAIController()


@app.get("/solar/status")
def solar_status(background_tasks: BackgroundTasks):
    status = solar_controller.get_status()
    # Auto-log solar reading
    if status.get("solar_output_kw") is not None:
        background_tasks.add_task(
            db.log_solar,
            status.get("solar_output_kw", 0),
            status.get("battery_charge_pct", 0),
            status.get("total_demand_kw", 0)
        )
    return status


@app.post("/solar/simulate")
def solar_simulate(hours: int = 24):
    return solar_controller.simulate(hours=hours)


@app.get("/solar/recommend")
def solar_recommend():
    return solar_controller.reroute_decision()


@app.get("/solar/history")
def solar_history(hours: int = 24):
    return {"history": db.get_solar_history(hours=hours)}


# ── CLAUDE AI ADVISOR ────────────────────────────────────

@app.post("/advisor")
async def advisor(body: AdvisorRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # Build context from the garden
    context_parts = []

    if body.include_garden_context:
        plants = db.list_plants()
        if plants:
            plant_summaries = []
            for p in plants[:8]:  # cap context size
                latest = db.get_latest_scan(p["id"])
                score_str = f"health {latest['health_score']}/100" if latest else "no scans yet"
                plant_summaries.append(
                    f"- {p['name']} ({p.get('variety','')}) · {score_str} · day {_days_since(p['planted_at'])}"
                )
            context_parts.append("GARDEN STATUS:\n" + "\n".join(plant_summaries))

        totals = db.get_harvest_totals()
        if totals.get("total_kg"):
            context_parts.append(
                f"HARVEST THIS SEASON: {totals['total_kg']} kg across {totals['entry_count']} harvests"
            )

        solar_hist = db.get_solar_history(hours=24)
        if solar_hist:
            latest_solar = solar_hist[-1]
            context_parts.append(
                f"SOLAR RIGHT NOW: {latest_solar.get('solar_kw', 0)} kW · battery {latest_solar.get('battery_pct', 0)}%"
            )

    if body.plant_id:
        timeline = db.get_plant_timeline(body.plant_id)
        if timeline:
            plant = timeline["plant"]
            context_parts.append(
                f"FOCUSED PLANT: {plant['name']} · trend {timeline['health_trend']} · "
                f"latest score {timeline['latest_score']} · {timeline['total_harvest_kg']} kg harvested total"
            )
            recent_events = timeline["events"][:5]
            event_strs = []
            for e in recent_events:
                if e["type"] == "scan":
                    event_strs.append(f"  Scan {e['date'][:10]}: score {e['health_score']}, alerts: {e.get('alerts', [])}")
                else:
                    event_strs.append(f"  Harvest {e['date'][:10]}: {e['kg']} kg — {e.get('notes','')}")
            if event_strs:
                context_parts.append("RECENT HISTORY:\n" + "\n".join(event_strs))

    system_prompt = """You are the Vedura AI advisor — a private, expert intelligence for off-grid homesteaders.
You speak with precision and care. You know plants, soil, solar energy, water systems, and off-grid living.
You give specific, actionable advice grounded in the actual data from this homestead.
You are not generic. You reference what you know about their garden. You are direct — no fluff.
Keep responses concise but complete. Use plain language. Never use markdown headers.
This session is private and leaves no record beyond this conversation."""

    user_message = body.message
    if context_parts:
        user_message = "\n\n".join(context_parts) + "\n\n---\n\nQUESTION: " + body.message

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}]
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Claude API error: {response.text}")

    data = response.json()
    reply = data["content"][0]["text"]
    return {
        "response": reply,
        "model": "claude-sonnet-4-6",
        "context_included": bool(context_parts)
    }


@app.post("/advisor/morning-brief")
async def morning_brief():
    """Generate a personalized morning brief from garden + solar data."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    plants = db.list_plants()
    totals = db.get_harvest_totals()
    solar_hist = db.get_solar_history(hours=8)

    plant_data = []
    for p in plants[:6]:
        latest = db.get_latest_scan(p["id"])
        plant_data.append({
            "name": p["name"],
            "variety": p.get("variety"),
            "day": _days_since(p["planted_at"]),
            "health": latest["health_score"] if latest else None,
            "trend": db.get_plant_timeline(p["id"]).get("health_trend") if latest else None
        })

    context = f"""
HOMESTEAD DATA — {datetime.utcnow().strftime('%A, %B %d')}

PLANTS:
{json.dumps(plant_data, indent=2)}

HARVEST TOTALS:
{json.dumps(totals, indent=2)}

SOLAR LAST 8 HOURS:
{json.dumps(solar_hist[-3:] if solar_hist else [], indent=2)}
"""

    system_prompt = """You are the Vedura morning advisor. Generate a brief, grounded morning intelligence report
for this homesteader. 3-5 bullet points. Each one specific and actionable based on the actual data.
Start directly — no greeting, no intro. Just the intelligence. Plain sentences, no markdown.
Tone: calm, knowledgeable, like a trusted advisor who knows the land."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 512,
                "system": system_prompt,
                "messages": [{"role": "user", "content": context}]
            }
        )

    data = response.json()
    return {
        "brief": data["content"][0]["text"],
        "generated_at": datetime.utcnow().isoformat(),
        "model": "claude-sonnet-4-6"
    }


# ── MYCELIUM NODE ────────────────────────────────────────

@app.post("/mycelium/node")
def setup_node(body: NodeSetup):
    node = db.get_or_create_node(
        name=body.name,
        lat=body.lat,
        lon=body.lon,
        location=body.location
    )
    return node


@app.get("/mycelium/node")
def get_node():
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM node LIMIT 1").fetchone()
        return dict(row) if row else {"status": "not configured"}


@app.post("/mycelium/sync")
async def manual_sync(background_tasks: BackgroundTasks):
    """Manually trigger sync of all unsynced records to Supabase."""
    if not SUPABASE_URL:
        return {"status": "skipped", "reason": "Supabase not configured"}
    background_tasks.add_task(_flush_sync_queue)
    return {"status": "queued"}


# ── KNOWLEDGE (existing) ─────────────────────────────────

KNOWLEDGE_TOPICS = [
    {"id": "composting", "title": "Composting", "summary": "Hot and cold composting methods for homesteaders."},
    {"id": "solar-sizing", "title": "Solar System Sizing", "summary": "How to size a solar array for off-grid living."},
    {"id": "water-harvesting", "title": "Water Harvesting", "summary": "Rainwater collection, storage, and filtration."},
    {"id": "seed-saving", "title": "Seed Saving", "summary": "Preserving genetic diversity through seed saving."},
    {"id": "soil-health", "title": "Soil Health", "summary": "Building living soil through biology, not chemistry."},
]


@app.get("/knowledge")
def knowledge_list():
    return {"topics": KNOWLEDGE_TOPICS}


@app.get("/knowledge/{topic_id}")
def knowledge_topic(topic_id: str):
    topic = next((t for t in KNOWLEDGE_TOPICS if t["id"] == topic_id), None)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


# ── BACKGROUND TASKS ─────────────────────────────────────

async def sync_scan_to_mycelium(scan_id: str):
    """Anonymously broadcast a scan result to Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    scan = db.get_scan(scan_id)
    if not scan:
        return
    node_row = None
    with db.get_conn() as conn:
        node_row = conn.execute("SELECT * FROM node LIMIT 1").fetchone()
    if not node_row:
        return
    payload = {
        "node_id": node_row["id"],
        "health_score": scan["health_score"],
        "scanned_at": scan["scanned_at"],
        "alert_count": len(scan.get("alerts", []))
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/broadcasts",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={"type": "scan", "data": payload}
            )
        db.mark_synced("scans", [scan_id])
    except Exception:
        pass


async def sync_harvest_to_mycelium(harvest_id: str):
    """Anonymously broadcast a harvest to Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    harvest = db.get_harvest(harvest_id)
    if not harvest:
        return
    plant = db.get_plant(harvest["plant_id"])
    node_row = None
    with db.get_conn() as conn:
        node_row = conn.execute("SELECT * FROM node LIMIT 1").fetchone()
    if not node_row or not plant:
        return
    payload = {
        "node_id": node_row["id"],
        "crop_name": plant["name"],
        "kg": harvest["kg"],
        "harvested_at": harvest["harvested_at"]
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/broadcasts",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={"type": "harvest", "data": payload}
            )
        db.mark_synced("harvests", [harvest_id])
    except Exception:
        pass


async def _flush_sync_queue():
    unsynced_scans = db.get_unsynced("scans")
    unsynced_harvests = db.get_unsynced("harvests")
    for s in unsynced_scans:
        await sync_scan_to_mycelium(s["id"])
    for h in unsynced_harvests:
        await sync_harvest_to_mycelium(h["id"])


# ── HELPERS ──────────────────────────────────────────────

def _days_since(date_str: str) -> int:
    try:
        planted = datetime.fromisoformat(date_str.replace("Z", ""))
        return (datetime.utcnow() - planted).days
    except Exception:
        return 0
