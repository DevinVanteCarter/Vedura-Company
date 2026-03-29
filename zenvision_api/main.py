#!/usr/bin/env python3
"""
Zen Vision FastAPI Backend
Solarpunk off-grid intelligence platform.
Plant health + Solar AI + Knowledge guide — all in one API.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import os
import shutil
import json

from .plant_health.image_analyzer import analyze_image
from .plant_health.video_analyzer import analyze_video
from .plant_health.solar_ai import SolarAIController

app = FastAPI(
    title="Zen Vision API",
    description="Solarpunk off-grid intelligence — plant health, solar AI, and community knowledge.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared solar controller per session (stateful simulation)
_solar_controller = SolarAIController()


def _load_plant_knowledge():
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, 'plant_health', 'plant_knowledge.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

PLANT_KNOWLEDGE = _load_plant_knowledge()

# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/", tags=["System"])
def root():
    return {
        "name": "Zen Vision API",
        "status": "online",
        "version": "1.0.0",
        "message": "May your plants thrive and your energy be sustainable 🌱☀️"
    }

@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy"}


# ─────────────────────────────────────────────
# PLANT HEALTH ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/plant/analyze/image", tags=["Plant Health"])
async def analyze_plant_image(file: UploadFile = File(...)):
    """
    Upload a plant image and get an instant AI health report.
    Detects: yellowing, burn, pests/spots, light stress.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        results = analyze_image(tmp_path, save_annotated=False)
        # Clean up non-serializable fields
        results.pop("annotated_image", None)
        results.pop("image_size", None)

        # Build a clean human-readable summary
        alerts = []
        if results.get("yellowing_suspected"):
            alerts.append(f"Yellowing detected ({results['yellowing_confidence']:.0%} confidence) — possible nutrient deficiency.")
        if results.get("burn_suspected"):
            alerts.append(f"Burn/browning detected ({results['burn_confidence']:.0%} confidence) — check light and fertilizer levels.")
        if results.get("spots_suspected"):
            alerts.append(f"Spots or pest clusters detected ({results['spots_confidence']:.0%} confidence) — inspect for mold or pests.")
        if results.get("light_stress_overexposed"):
            alerts.append("Overexposure detected — plant may be getting too much direct light.")
        if results.get("light_stress_underexposed"):
            alerts.append("Underexposure detected — plant may need more light.")

        return {
            "status": "ok",
            "health_score": _calculate_health_score(results),
            "alerts": alerts,
            "raw": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@app.post("/plant/analyze/video", tags=["Plant Health"])
async def analyze_plant_video(
    file: UploadFile = File(...),
    sample_rate: int = 5
):
    """
    Upload a plant video and get a trend analysis over time.
    Detects health trajectory: improving, stable, or declining.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        results = analyze_video(tmp_path, sample_rate=sample_rate)
        # Remove verbose frame data for API response
        results.pop("frame_results", None)

        trend_message = {
            "declining_green": "Plant health is declining — take action soon.",
            "improving_green": "Plant health is improving — keep it up!",
            "stable": "Plant health is stable."
        }.get(results.get("trend"), "Unable to determine trend.")

        return {
            "status": "ok",
            "trend_message": trend_message,
            "raw": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


# ─────────────────────────────────────────────
# SOLAR AI ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/solar/status", tags=["Solar AI"])
def solar_status():
    """
    Get the current solar system status — output, battery, demand, routing.
    """
    try:
        data = _solar_controller.step()
        decision = _solar_controller.reroute_decision()
        return {
            "status": "ok",
            "solar_output_kw": data["solar_output"],
            "battery_charge_pct": data["battery_charge"],
            "battery_health_pct": data["battery_health"],
            "total_demand_kw": data["total_demand"],
            "grid_usage_kw": data["grid_usage"],
            "unused_solar_kw": data["unused_solar"],
            "grid_price_per_kwh": data["grid_price"],
            "load_routing": data["routing"],
            "recommendations": decision["actions"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/solar/simulate", tags=["Solar AI"])
def solar_simulate(hours: int = 24):
    """
    Run a solar power simulation for 1-24 hours.
    Returns hour-by-hour breakdown of solar, battery, and grid usage.
    """
    if not 1 <= hours <= 24:
        raise HTTPException(status_code=400, detail="Hours must be between 1 and 24.")

    controller = SolarAIController()
    timeline = []
    for _ in range(hours):
        data = controller.step()
        timeline.append(data)

    return {
        "status": "ok",
        "hours_simulated": hours,
        "total_power_distributed_kwh": round(controller.total_power_distributed, 2),
        "final_battery_pct": round(controller.battery_charge_level, 1),
        "timeline": timeline
    }


@app.get("/solar/recommend", tags=["Solar AI"])
def solar_recommend():
    """
    Get AI-generated power management recommendations based on current state.
    """
    try:
        decision = _solar_controller.reroute_decision()
        return {
            "status": "ok",
            "battery_charge_pct": decision["battery_charge"],
            "grid_price_per_kwh": decision["grid_price"],
            "actions": decision["actions"],
            "routing": decision["routing"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# KNOWLEDGE GUIDE ENDPOINTS
# ─────────────────────────────────────────────

KNOWLEDGE_BASE = {
    "solar": {
        "title": "Solar power basics",
        "content": "A basic off-grid solar setup needs panels, a charge controller, batteries, and an inverter. Start with your daily kWh usage to size your system.",
        "tags": ["solar", "power", "beginner"]
    },
    "water": {
        "title": "Water collection and filtration",
        "content": "Rainwater harvesting, gravity-fed systems, and biosand filters are the three pillars of off-grid water. Always test before drinking.",
        "tags": ["water", "filtration", "beginner"]
    },
    "plants": {
        "title": "Growing food off-grid",
        "content": "Start with easy crops: tomatoes, beans, kale, and herbs. Companion planting reduces pests. Soil health is everything — compost first.",
        "tags": ["plants", "food", "gardening"]
    },
    "battery": {
        "title": "Battery storage systems",
        "content": "LiFePO4 batteries are the gold standard for off-grid — safe, long-lasting, and efficient. Size your bank for 2-3 days of autonomy.",
        "tags": ["battery", "storage", "solar"]
    },
    "shelter": {
        "title": "Off-grid shelter options",
        "content": "Tiny homes, earthships, yurts, and converted vehicles all have different tradeoffs. Insulation is your biggest lever for energy efficiency.",
        "tags": ["shelter", "housing", "beginner"]
    }
}

@app.get("/knowledge", tags=["Knowledge Guide"])
def list_knowledge():
    """List all available knowledge guide topics."""
    return {
        "status": "ok",
        "topics": [
            {"id": k, "title": v["title"], "tags": v["tags"]}
            for k, v in KNOWLEDGE_BASE.items()
        ]
    }

@app.get("/knowledge/{topic_id}", tags=["Knowledge Guide"])
def get_knowledge(topic_id: str):
    """Get a specific knowledge guide topic."""
    topic = KNOWLEDGE_BASE.get(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found.")
    return {"status": "ok", "topic": topic}


@app.get("/knowledge/plants", tags=["Knowledge Guide"])
def list_plant_knowledge():
    """List detailed Ohio plant knowledge topics."""
    return {"status": "ok", "topics": PLANT_KNOWLEDGE}


@app.get("/knowledge/plants/{topic_id}", tags=["Knowledge Guide"])
def get_plant_knowledge(topic_id: str):
    """Get a specific Ohio plant knowledge topic."""
    topic = PLANT_KNOWLEDGE.get(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Plant topic '{topic_id}' not found.")
    return {"status": "ok", "topic": topic}


# ─────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────

def _calculate_health_score(results: dict) -> int:
    """Calculate a 0-100 plant health score from analysis results."""
    score = 100
    score -= int(results.get("yellowing_confidence", 0) * 34)
    score -= int(results.get("burn_confidence", 0) * 28)
    score -= int(results.get("spots_confidence", 0) * 22)
    score -= int(results.get("light_over_confidence", 0) * 12)
    score -= int(results.get("light_under_confidence", 0) * 12)

    vegetation_coverage = results.get("vegetation_coverage", 1.0)
    if vegetation_coverage < 0.12:
        score -= int((0.12 - vegetation_coverage) * 100 * 0.6)

    if results.get("plant_pixel_count", 0) < 900:
        score -= 8

    return max(0, min(100, score))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
