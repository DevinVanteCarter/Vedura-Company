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


# ── SOLAR ────────────────────────────────────────────────

def _solar_irradiance_estimate(cloud_cover: int) -> str:
    if cloud_cover < 20: return "high"
    if cloud_cover < 50: return "medium"
    if cloud_cover < 80: return "low"
    return "none"

def _estimate_uv(cloud_cover: int) -> int:
    from datetime import datetime as _dt
    hour = _dt.now().hour
    if hour < 7 or hour > 19: return 0
    angle = math.pi * (hour - 7) / 12.0
    time_factor = max(0.0, math.sin(angle))
    cloud_factor = 1.0 - (cloud_cover / 100.0) * 0.75
    return round(11 * time_factor * cloud_factor)

def _solar_rating(avg_clouds: float, rain_chance: int) -> str:
    if avg_clouds < 20 and rain_chance < 20: return "excellent"
    if avg_clouds < 50 and rain_chance < 50: return "good"
    if avg_clouds < 75:                      return "fair"
    return "poor"

def _day_plant_risk(humidity: float, low_f: float, rain_chance: int) -> str:
    if humidity > 80 and low_f > 60:       return "high"
    if humidity > 70 and rain_chance > 40: return "medium"
    return "low"

def _overall_disease_risk(humidity: int, temp_f: float, forecast: list) -> str:
    if humidity > 80 and temp_f > 60: return "high"
    rain_days = sum(1 for d in forecast if d["rain_chance_pct"] > 40)
    if humidity > 70 and rain_days > 1: return "medium"
    return "low"

def _solar_outlook(irradiance: str, forecast: list) -> str:
    good = sum(1 for d in forecast if d["solar_rating"] in ("excellent", "good"))
    if irradiance in ("high", "medium") and good >= 3: return "strong"
    if good >= 2:                                       return "moderate"
    return "weak"

def _homestead_briefing(temp_f, humidity, irradiance, frost_warning,
                        storm_incoming, disease_risk, forecast) -> str:
    if frost_warning:
        return "Frost risk tonight — cover your seedlings before dark and bring tender plants inside."
    storm_day = next((d for d in forecast[:3] if d["rain_chance_pct"] > 70), None)
    if storm_incoming and storm_day:
        return (f"Storm incoming {storm_day['day']} — harvest what's ready now and charge your battery to 100%.")
    if disease_risk == "high":
        return "High humidity and warmth are prime fungal conditions — inspect your plants closely today."
    if irradiance == "high":
        return "Strong solar day — run your water pump, charge the battery fully, and defer all grid draw."
    if irradiance == "none":
        return "Heavy cloud cover today — conserve battery and defer non-essential loads until conditions improve."
    if temp_f < 45:
        return "Cold day — check on cold-sensitive crops and protect water lines from freezing overnight."
    return "Conditions are favorable — a good day to tend the garden and top off your battery bank."


@app.get("/solar/status", tags=["Solar AI"])
def solar_status(background_tasks: BackgroundTasks):
    """Current solar output, battery %, demand, and routing."""
    try:
        from datetime import datetime as _dt
        controller = SolarAIController()
        controller.simulation_hour = _dt.now().hour
        data = controller.step()
        decision = controller.reroute_decision()
        result = {
            "status": "ok",
            "solar_output_kw":    data["solar_output"],
            "battery_charge_pct": data["battery_charge"],
            "battery_health_pct": data["battery_health"],
            "total_demand_kw":    data["total_demand"],
            "grid_usage_kw":      data["grid_usage"],
            "unused_solar_kw":    data["unused_solar"],
            "grid_price_per_kwh": data["grid_price"],
            "load_routing":       data["routing"],
            "recommendations":    decision["actions"],
        }
        background_tasks.add_task(
            db.log_solar,
            result["solar_output_kw"],
            result["battery_charge_pct"],
            result["total_demand_kw"],
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/solar/simulate", tags=["Solar AI"])
def solar_simulate(hours: int = 24):
    if not 1 <= hours <= 24:
        raise HTTPException(status_code=400, detail="Hours must be between 1 and 24.")
    controller = SolarAIController()
    timeline = []
    for _ in range(hours):
        timeline.append(controller.step())
    return {
        "status": "ok",
        "hours_simulated": hours,
        "total_power_distributed_kwh": round(controller.total_power_distributed, 2),
        "final_battery_pct": round(controller.battery_charge_level, 1),
        "timeline": timeline,
    }


@app.get("/solar/recommend", tags=["Solar AI"])
def solar_recommend():
    try:
        from datetime import datetime as _dt
        controller = SolarAIController()
        controller.simulation_hour = _dt.now().hour
        controller.step()
        decision = controller.reroute_decision()
        return {
            "status": "ok",
            "battery_charge_pct": decision["battery_charge"],
            "grid_price_per_kwh": decision["grid_price"],
            "actions": decision["actions"],
            "routing": decision["routing"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/solar/real", tags=["Solar AI"])
def solar_real(lat: float = 39.27, lon: float = -84.26, capacity: float = 5.0):
    try:
        data = get_real_solar_data(lat=lat, lon=lon, system_capacity_kw=capacity)
        return {"status": "ok", **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/solar/history", tags=["Solar AI"])
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


# ── HOMESTEAD INTELLIGENCE ───────────────────────────────

_OHIO_CROPS: dict = {
    1:  [("Onions","Start seeds indoors under lights",100,"12-14 wks before last frost"),
         ("Peppers","Start seeds indoors",80,"10-12 wks before transplant"),
         ("Lettuce","Start indoors under grow lights",45,"Transplant outside in March")],
    2:  [("Onions","Start seeds indoors",100,"12-14 wks before last frost April 15"),
         ("Peppers","Start seeds indoors",80,"10-12 wks before transplant date"),
         ("Tomatoes","Start seeds indoors",75,"6-8 wks before last frost April 15"),
         ("Lettuce","Start indoors under grow lights",45,"Transplant outside in April")],
    3:  [("Lettuce","Direct sow or transplant",45,"Cold-tolerant — plant now"),
         ("Spinach","Direct sow",40,"Hardy to 20°F — plant now"),
         ("Kale","Start indoors or direct sow",55,"Frost-tolerant"),
         ("Onions","Transplant seedlings outdoors",100,"Harden off before planting"),
         ("Tomatoes","Start indoors",75,"6 wks before last frost April 15"),
         ("Peppers","Start indoors",80,"8 wks before transplant date")],
    4:  [("Tomatoes","Start indoors or transplant after May 1",75,"After last frost Apr 15"),
         ("Peppers","Start indoors — transplant after May 15",80,"Needs warm soil 65°F+"),
         ("Cucumbers","Start indoors — transplant after May 15",55,"Frost-sensitive"),
         ("Squash","Start indoors or direct sow after May 1",50,"Plant after last frost"),
         ("Basil","Start indoors now",60,"Transplant after last frost"),
         ("Lettuce","Direct sow — ideal conditions",45,"Sow every 2 wks for continuous harvest"),
         ("Spinach","Direct sow",40,"Bolt-resistant variety for spring"),
         ("Kale","Direct sow or transplant",55,"Excellent spring crop")],
    5:  [("Tomatoes","Transplant outdoors — soil 60°F+",75,"Last frost past — go time"),
         ("Peppers","Transplant outdoors after May 15",80,"Soil must be warm 65°F+"),
         ("Cucumbers","Direct sow or transplant",55,"Full sun, consistent moisture"),
         ("Squash","Direct sow outdoors",50,"1 inch water per week"),
         ("Beans","Direct sow",55,"1 inch deep, 6 inches apart"),
         ("Corn","Direct sow when soil hits 65°F",75,"Plant in blocks for pollination"),
         ("Basil","Transplant outdoors",60,"Pinch flowers to keep producing")],
    6:  [("Beans","Succession plant every 2 weeks",55,"Keep harvesting for continuous yield"),
         ("Cucumbers","Last chance to start for summer",55,"Needs full season to produce"),
         ("Basil","Direct sow outdoors",60,"Peak basil season"),
         ("Corn","Last succession planting",75,"Plant for fall harvest")],
    7:  [("Kale","Start for fall harvest",55,"Tastes better after frost"),
         ("Spinach","Direct sow for fall",40,"8 wks before first frost Oct 15"),
         ("Lettuce","Start for fall harvest",45,"Bolt risk reduces as temps cool"),
         ("Beans","Last direct sow for season",55,"Must mature before Oct 15 frost")],
    8:  [("Kale","Direct sow for fall — best crop",55,"Hardy through light frost"),
         ("Spinach","Direct sow for fall",40,"September harvest possible"),
         ("Lettuce","Direct sow for fall",45,"Perfect fall conditions ahead"),
         ("Garlic","Prepare beds for October planting",240,"Plant cloves in October for next year")],
    9:  [("Garlic","Plant cloves 2 inches deep",240,"4-6 wks before freeze — mulch after"),
         ("Kale","Last direct sow",55,"Hardy through light frost"),
         ("Spinach","Last direct sow",40,"Can overwinter with row cover")],
    10: [("Garlic","Plant now if not yet done",240,"Mulch heavily after planting"),
         ("Cover Crops","Winter rye or crimson clover",0,"Protect and feed soil over winter")],
    11: [("Cover Crops","Last chance to establish",0,"Soil protection for winter")],
    12: [],
}

_OHIO_HARVEST: dict = {
    4:  [{"crop":"Overwintered Spinach","ready":"Harvest before it bolts — prime now"},
         {"crop":"Overwintered Kale","ready":"Peak flavor after frost — harvest outer leaves"}],
    5:  [{"crop":"Lettuce","ready":"March plantings ready — harvest before heat sets in"},
         {"crop":"Spinach","ready":"March plantings mature — harvest before bolting"},
         {"crop":"Radishes","ready":"April plantings ready in 25-30 days"}],
    6:  [{"crop":"Lettuce","ready":"May plantings ready — harvest before summer heat"},
         {"crop":"Peas","ready":"April plantings mature — check pods daily"}],
    7:  [{"crop":"Cucumbers","ready":"First harvests — check daily once flowering"},
         {"crop":"Beans","ready":"May plantings mature — harvest before seeds develop"},
         {"crop":"Zucchini","ready":"Harvest at 6-8 inches — don't let over-grow"}],
    8:  [{"crop":"Tomatoes","ready":"Main harvest season — check daily"},
         {"crop":"Peppers","ready":"Harvest when color develops fully"},
         {"crop":"Corn","ready":"Check silk browning and kernel fill"},
         {"crop":"Cucumbers","ready":"Peak production — harvest every 2 days"}],
    9:  [{"crop":"Winter Squash","ready":"Harvest before first frost — skin must be hard"},
         {"crop":"Dry Beans","ready":"Leave on vine until pods rattle"},
         {"crop":"Tomatoes","ready":"Frost risk — pick green tomatoes, ripen indoors"}],
    10: [{"crop":"Root Vegetables","ready":"Carrots, beets, turnips — frost improves sweetness"},
         {"crop":"Brussels Sprouts","ready":"Best after frost — harvest bottom-up"}],
}

_DISEASE_MAP = {
    "Tomatoes":  "Early Blight",
    "Peppers":   "Phytophthora Blight",
    "Cucumbers": "Downy Mildew",
    "Squash":    "Powdery Mildew",
    "Beans":     "Bean Rust",
    "Corn":      "Gray Leaf Spot",
}


@app.get("/weather", tags=["Homestead"])
def get_weather(lat: float = 39.2686, lon: float = -84.2631):
    from collections import defaultdict
    from datetime import datetime as _dt
    api_key = (os.environ.get("OPENWEATHER_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENWEATHER_API_KEY not set.")
    try:
        cw = requests.get("https://api.openweathermap.org/data/2.5/weather",
            params={"lat":lat,"lon":lon,"appid":api_key,"units":"imperial"}, timeout=10)
        cw.raise_for_status(); cw = cw.json()
        fw = requests.get("https://api.openweathermap.org/data/2.5/forecast",
            params={"lat":lat,"lon":lon,"appid":api_key,"units":"imperial","cnt":40}, timeout=10)
        fw.raise_for_status(); fw = fw.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {e}")

    temp_f       = round(cw["main"]["temp"])
    feels_like_f = round(cw["main"]["feels_like"])
    humidity     = cw["main"]["humidity"]
    description  = cw["weather"][0]["description"].capitalize()
    wind_mph     = round(cw["wind"]["speed"])
    cloud_cover  = cw["clouds"]["all"]
    city         = cw.get("name","")
    country      = cw.get("sys",{}).get("country","")
    location     = f"{city}, {country}" if city else f"{lat:.4f}°N, {abs(lon):.4f}°W"
    irradiance   = _solar_irradiance_estimate(cloud_cover)
    uv_index     = _estimate_uv(cloud_cover)

    daily: dict = defaultdict(list)
    for item in fw["list"]:
        daily[item["dt_txt"][:10]].append(item)
    forecast_5day = []
    for date_str, items in sorted(daily.items())[:5]:
        temps  = [i["main"]["temp"] for i in items]
        pops   = [i.get("pop",0)    for i in items]
        clouds = [i["clouds"]["all"] for i in items]
        humids = [i["main"]["humidity"] for i in items]
        midday = next((i for i in items if "12:" in i["dt_txt"]), items[len(items)//2])
        forecast_5day.append({
            "date": date_str,
            "day":  _dt.strptime(date_str, "%Y-%m-%d").strftime("%A"),
            "high_f": round(max(temps)), "low_f": round(min(temps)),
            "description": midday["weather"][0]["description"].capitalize(),
            "rain_chance_pct": round(max(pops)*100),
            "frost_risk": round(min(temps)) < 36,
            "solar_rating": _solar_rating(sum(clouds)/len(clouds), round(max(pops)*100)),
            "plant_risk":   _day_plant_risk(sum(humids)/len(humids), round(min(temps)), round(max(pops)*100)),
        })
    frost_warning  = any(d["low_f"] < 32          for d in forecast_5day[:2])
    storm_incoming = any(d["rain_chance_pct"] > 70 for d in forecast_5day[:3])
    disease_risk   = _overall_disease_risk(humidity, temp_f, forecast_5day)
    solar_out      = _solar_outlook(irradiance, forecast_5day)
    briefing       = _homestead_briefing(temp_f, humidity, irradiance, frost_warning,
                                         storm_incoming, disease_risk, forecast_5day)
    return {
        "status": "ok", "location": location,
        "current": {"temp_f":temp_f,"feels_like_f":feels_like_f,"humidity":humidity,
                    "description":description,"wind_mph":wind_mph,"uv_index":uv_index,
                    "cloud_cover_pct":cloud_cover,"solar_irradiance_estimate":irradiance},
        "forecast_5day": forecast_5day,
        "alerts": {"frost_warning":frost_warning,"frost_date_last":"May 1",
                   "storm_incoming":storm_incoming,"drought_risk":all(d["rain_chance_pct"]<10 for d in forecast_5day),
                   "plant_disease_risk":disease_risk,"solar_outlook":solar_out},
        "homestead_briefing": briefing,
    }


@app.get("/crops", tags=["Homestead"])
def get_crops(lat: float = 39.2686, lon: float = -84.2631):
    from datetime import datetime as _dt
    month = _dt.now().month
    season = ("spring" if month in (3,4,5) else "summer" if month in (6,7,8)
              else "fall" if month in (9,10,11) else "winter")
    return {
        "location":"Loveland, OH","usda_zone":"6b",
        "last_frost_date":"April 15","first_frost_date":"October 15",
        "current_season":season,
        "plant_now":[{"crop":c,"action":a,"days_to_harvest":d,"notes":n}
                     for c,a,d,n in _OHIO_CROPS.get(month,[])],
        "harvest_soon": _OHIO_HARVEST.get(month,[]),
        "watch_list":   [],
    }


@app.get("/homestead", tags=["Homestead"])
def get_homestead(lat: float = 39.2686, lon: float = -84.2631):
    from collections import defaultdict
    from datetime import datetime as _dt
    api_key = (os.environ.get("OPENWEATHER_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENWEATHER_API_KEY not set.")
    try:
        cw = requests.get("https://api.openweathermap.org/data/2.5/weather",
            params={"lat":lat,"lon":lon,"appid":api_key,"units":"imperial"}, timeout=10)
        cw.raise_for_status(); cw = cw.json()
        fw = requests.get("https://api.openweathermap.org/data/2.5/forecast",
            params={"lat":lat,"lon":lon,"appid":api_key,"units":"imperial","cnt":40}, timeout=10)
        fw.raise_for_status(); fw = fw.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Weather fetch failed: {e}")

    temp_f       = round(cw["main"]["temp"])
    feels_like_f = round(cw["main"]["feels_like"])
    humidity     = cw["main"]["humidity"]
    description  = cw["weather"][0]["description"].capitalize()
    wind_mph     = round(cw["wind"]["speed"])
    cloud_cover  = cw["clouds"]["all"]
    city         = cw.get("name",""); country = cw.get("sys",{}).get("country","")
    location     = f"{city}, {country}" if city else f"{lat:.4f}°N, {abs(lon):.4f}°W"
    irradiance   = _solar_irradiance_estimate(cloud_cover)
    uv_index     = _estimate_uv(cloud_cover)

    daily: dict = defaultdict(list)
    for item in fw["list"]:
        daily[item["dt_txt"][:10]].append(item)
    forecast_5day = []
    for date_str, items in sorted(daily.items())[:5]:
        temps  = [i["main"]["temp"] for i in items]
        pops   = [i.get("pop",0)    for i in items]
        clouds = [i["clouds"]["all"] for i in items]
        humids = [i["main"]["humidity"] for i in items]
        midday = next((i for i in items if "12:" in i["dt_txt"]), items[len(items)//2])
        forecast_5day.append({
            "date": date_str,
            "day":  _dt.strptime(date_str, "%Y-%m-%d").strftime("%A"),
            "high_f": round(max(temps)), "low_f": round(min(temps)),
            "description": midday["weather"][0]["description"].capitalize(),
            "rain_chance_pct": round(max(pops)*100),
            "frost_risk": round(min(temps)) < 36,
            "solar_rating": _solar_rating(sum(clouds)/len(clouds), round(max(pops)*100)),
            "plant_risk":   _day_plant_risk(sum(humids)/len(humids), round(min(temps)), round(max(pops)*100)),
        })

    frost_warning  = any(d["low_f"] < 32          for d in forecast_5day[:2])
    storm_incoming = any(d["rain_chance_pct"] > 70 for d in forecast_5day[:3])
    drought_risk   = all(d["rain_chance_pct"] < 10 for d in forecast_5day)
    disease_risk   = _overall_disease_risk(humidity, temp_f, forecast_5day)
    solar_out      = _solar_outlook(irradiance, forecast_5day)
    briefing       = _homestead_briefing(temp_f, humidity, irradiance, frost_warning,
                                         storm_incoming, disease_risk, forecast_5day)

    weather_summary = {
        "status":"ok","location":location,
        "current":{"temp_f":temp_f,"feels_like_f":feels_like_f,"humidity":humidity,
                   "description":description,"wind_mph":wind_mph,"uv_index":uv_index,
                   "cloud_cover_pct":cloud_cover,"solar_irradiance_estimate":irradiance},
        "forecast_5day": forecast_5day,
        "alerts":{"frost_warning":frost_warning,"frost_date_last":"May 1",
                  "storm_incoming":storm_incoming,"drought_risk":drought_risk,
                  "plant_disease_risk":disease_risk,"solar_outlook":solar_out},
        "homestead_briefing": briefing,
    }

    month  = _dt.now().month
    season = ("spring" if month in (3,4,5) else "summer" if month in (6,7,8)
              else "fall" if month in (9,10,11) else "winter")
    plant_now = [{"crop":c,"action":a,"days_to_harvest":d,"notes":n}
                 for c,a,d,n in _OHIO_CROPS.get(month,[])]
    watch_list = []
    if disease_risk in ("high","medium"):
        for item in plant_now:
            crop = item["crop"]
            if crop in _DISEASE_MAP:
                watch_list.append({
                    "crop":crop,"risk":_DISEASE_MAP[crop],
                    "reason":f"{'High' if disease_risk=='high' else 'Elevated'} humidity ({humidity}%) forecast",
                    "action":"Inspect leaves, apply neem oil preventatively",
                })
    crop_data = {
        "location":"Loveland, OH","usda_zone":"6b",
        "last_frost_date":"April 15","first_frost_date":"October 15",
        "current_season":season,
        "plant_now":plant_now,"harvest_soon":_OHIO_HARVEST.get(month,[]),"watch_list":watch_list,
    }

    try:
        sol = SolarAIController()
        sol.simulation_hour = _dt.now().hour
        sol_data = sol.step(); sol_dec = sol.reroute_decision()
        battery  = sol_data["battery_charge"]
        solar_summary = {"current_output_kw":sol_data["solar_output"],"battery_pct":battery,
                         "recommendation":sol_dec["actions"][0] if sol_dec["actions"] else "System nominal",
                         "solar_irradiance":irradiance}
    except Exception:
        battery = 50
        solar_summary = {"current_output_kw":0,"battery_pct":battery,
                         "recommendation":"Solar data temporarily unavailable","solar_irradiance":irradiance}

    cloud_impact = {"high":"Strong solar output — panels at peak generation",
                    "medium":"Partial clouds — output reduced ~30%",
                    "low":"Heavy overcast — output reduced ~65%",
                    "none":"No solar generation today"}.get(irradiance,"—")
    connections = {
        "weather_affects_solar": cloud_impact,
        "weather_affects_crops": (
            "High humidity — fungal disease risk for tomatoes & peppers" if disease_risk=="high" else
            "Elevated moisture — monitor for leaf disease"               if disease_risk=="medium" else
            "Conditions favorable for most crops"),
        "solar_affects_loads": (
            f"Battery {battery}% — charge before storm arrives"  if storm_incoming and battery<80 else
            f"Battery {battery}% — strong output, run loads now" if irradiance in ("high","medium") else
            f"Low output — conserve battery (currently {battery}%)"),
        "crops_need_attention": (
            f"{watch_list[0]['crop']} flagged — scan recommended" if watch_list else
            "No active crop alerts — conditions stable"),
    }

    actions = []
    if frost_warning:    actions.append("Cover seedlings tonight — frost risk in next 48 hours")
    if storm_incoming and battery < 80:
        actions.append("Charge battery to 100% before storm arrives")
        actions.append("Harvest any ripe crops before storm day")
    if disease_risk == "high": actions.append(f"Inspect plants for fungal disease — {humidity}% humidity today")
    if irradiance in ("high","medium") and battery < 60:
        actions.append("Run water pump and high-draw loads — strong solar output today")
    for w in watch_list[:2]:
        actions.append(f"Check {w['crop']} for {w['risk']} — {w['action']}")
    if not actions:
        actions.append("Conditions favorable — good day to tend the garden")
        actions.append("Top off battery bank while solar is available")

    return {
        "briefing": briefing,
        "weather_summary": weather_summary,
        "solar_summary": solar_summary,
        "crop_data": crop_data,
        "crop_alerts": watch_list,
        "plant_health_context": (
            "High humidity today — tomato blight risk elevated. Use the plant scanner." if disease_risk=="high" else
            "Elevated moisture — monitor for fungal signs on leaves." if disease_risk=="medium" else
            "Conditions favorable — no active plant disease risk detected."),
        "priority_actions": [f"{i+1}. {a}" for i,a in enumerate(actions)],
        "connections": connections,
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
