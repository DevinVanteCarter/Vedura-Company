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
import anthropic

from plant_health.image_analyzer import analyze_image
from plant_health.video_analyzer import analyze_video
from plant_health.solar_ai import SolarAIController, get_real_solar_data

app = FastAPI(
    title="Zen Vision API",
    description="Solarpunk off-grid intelligence — plant health, solar AI, and community knowledge.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://zen-vision-sigma.vercel.app", "https://vedura.co", "https://www.vedura.co", "https://theveduracompany.com", "https://www.theveduracompany.com", "http://localhost:3001"],
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

@app.get("/debug/env", tags=["System"])
def debug_env():
    return {
        "plantnet_key_set": bool(os.environ.get("PLANTNET_API_KEY")),
        "plantid_key_set": bool(os.environ.get("PLANT_ID_API_KEY")),
    }


# ─────────────────────────────────────────────
# PLANT HEALTH ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/plant/analyze/image", tags=["Plant Health"])
async def analyze_plant_image(file: UploadFile = File(...)):
    """
    Upload a plant image and get an instant AI health report.
    Detects: yellowing, burn, pests/spots, light stress.
    """
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        results = analyze_image(tmp_path, save_annotated=False)
        # Clean up non-serializable fields
        results.pop("annotated_image", None)
        results.pop("image_size", None)

        # Build alerts — use ML disease name when available, fall back to generic
        alerts = []
        disease = results.get("disease_name", "")
        severity = results.get("severity", "")
        top_preds = results.get("top_predictions", [])
        top_conf = top_preds[0]["confidence"] if top_preds else 0.0

        if results.get("model_used") == "onnx_plantvillage_mobilenetv2":
            species_note = results.get("species_note", "")
            if species_note:
                alerts.append(species_note)
            elif not results.get("is_healthy") and disease and disease != "Healthy":
                sev_label = f" ({severity})" if severity and severity != "none" else ""
                alerts.append(f"{disease}{sev_label} — {int(top_conf * 100)}% confidence.")
                treatment = results.get("treatment", "")
                if treatment:
                    alerts.append(f"Treatment: {treatment}")
            # Light stress still from raw pixel data — not detected by ML model
            if results.get("light_stress_overexposed"):
                alerts.append("Overexposure detected — plant may be getting too much direct light.")
            if results.get("light_stress_underexposed"):
                alerts.append("Underexposure detected — plant may need more light.")
        else:
            # CV fallback — generic alerts
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
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


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
    Each request creates a fresh controller seeded to the real current hour
    so solar output reflects the actual time of day and battery never drains
    between API calls.
    """
    try:
        from datetime import datetime as _dt
        controller = SolarAIController()
        controller.simulation_hour = _dt.now().hour
        data = controller.step()
        decision = controller.reroute_decision()
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
        from datetime import datetime as _dt
        controller = SolarAIController()
        controller.simulation_hour = _dt.now().hour
        controller.step()  # advance one step to populate state
        decision = controller.reroute_decision()
        return {
            "status": "ok",
            "battery_charge_pct": decision["battery_charge"],
            "grid_price_per_kwh": decision["grid_price"],
            "actions": decision["actions"],
            "routing": decision["routing"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/solar/real", tags=["Solar AI"])
def solar_real(
    lat: float = 39.27,
    lon: float = -84.26,
    capacity: float = 5.0
):
    """
    Get real solar production data from NREL PVWatts v8.
    Defaults to Loveland, Ohio. Pass lat/lon for any location.
    Returns monthly production estimates, current output, and recommendations.
    """
    try:
        data = get_real_solar_data(lat=lat, lon=lon, system_capacity_kw=capacity)
        return {"status": "ok", **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# HOMESTEAD — WEATHER ENGINE
# ─────────────────────────────────────────────

def _solar_irradiance_estimate(cloud_cover: int) -> str:
    if cloud_cover < 20:   return "high"
    if cloud_cover < 50:   return "medium"
    if cloud_cover < 80:   return "low"
    return "none"

def _estimate_uv(cloud_cover: int) -> int:
    from datetime import datetime as _dt
    hour = _dt.now().hour
    if hour < 7 or hour > 19:
        return 0
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
    if humidity > 80 and low_f > 60:           return "high"
    if humidity > 70 and rain_chance > 40:     return "medium"
    return "low"

def _overall_disease_risk(humidity: int, temp_f: float, forecast: list) -> str:
    if humidity > 80 and temp_f > 60:
        return "high"
    rain_days = sum(1 for d in forecast if d["rain_chance_pct"] > 40)
    if humidity > 70 and rain_days > 1:
        return "medium"
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
        return (f"Storm incoming {storm_day['day']} — harvest what's ready now "
                f"and charge your battery to 100%.")
    if disease_risk == "high":
        return ("High humidity and warmth are prime fungal conditions — "
                "inspect your plants closely today.")
    if irradiance == "high":
        return ("Strong solar day — run your water pump, charge the battery fully, "
                "and defer all grid draw.")
    if irradiance == "none":
        return ("Heavy cloud cover today — conserve battery and defer non-essential "
                "loads until conditions improve.")
    if temp_f < 45:
        return ("Cold day — check on cold-sensitive crops and protect water lines "
                "from freezing overnight.")
    return ("Conditions are favorable — a good day to tend the garden and "
            "top off your battery bank.")


@app.get("/weather", tags=["Homestead"])
def get_weather(lat: float = 39.2686, lon: float = -84.2631):
    """
    Get current weather + 5-day forecast with homestead intelligence.
    Returns plant disease risk, frost warnings, solar outlook, and a
    one-sentence homestead briefing. Defaults to Loveland, Ohio.
    """
    from collections import defaultdict
    from datetime import datetime as _dt

    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Weather unavailable: OPENWEATHER_API_KEY not set."
        )

    try:
        # ── Current weather ──────────────────────────────────────────────
        cw_resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "imperial"},
            timeout=10
        )
        cw_resp.raise_for_status()
        cw = cw_resp.json()

        # ── 5-day / 3-hour forecast ──────────────────────────────────────
        fc_resp = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"lat": lat, "lon": lon, "appid": api_key,
                    "units": "imperial", "cnt": 40},
            timeout=10
        )
        fc_resp.raise_for_status()
        fw = fc_resp.json()

        # ── Parse current ────────────────────────────────────────────────
        temp_f       = round(cw["main"]["temp"])
        feels_like_f = round(cw["main"]["feels_like"])
        humidity     = cw["main"]["humidity"]
        description  = cw["weather"][0]["description"].capitalize()
        wind_mph     = round(cw["wind"]["speed"])
        cloud_cover  = cw["clouds"]["all"]
        city         = cw.get("name", "")
        country      = cw.get("sys", {}).get("country", "")
        location     = f"{city}, {country}" if city else f"{lat:.4f}°N, {abs(lon):.4f}°W"

        irradiance = _solar_irradiance_estimate(cloud_cover)
        uv_index   = _estimate_uv(cloud_cover)

        # ── Aggregate forecast to daily ──────────────────────────────────
        daily: dict = defaultdict(list)
        for item in fw["list"]:
            daily[item["dt_txt"][:10]].append(item)

        forecast_5day = []
        for date_str, items in sorted(daily.items())[:5]:
            temps    = [i["main"]["temp"]     for i in items]
            pops     = [i.get("pop", 0)       for i in items]
            clouds   = [i["clouds"]["all"]    for i in items]
            humids   = [i["main"]["humidity"] for i in items]

            high_f      = round(max(temps))
            low_f       = round(min(temps))
            rain_chance = round(max(pops) * 100)
            avg_clouds  = sum(clouds) / len(clouds)
            avg_humidity= sum(humids) / len(humids)

            midday = next(
                (i for i in items if "12:" in i["dt_txt"]),
                items[len(items) // 2]
            )
            desc     = midday["weather"][0]["description"].capitalize()
            day_name = _dt.strptime(date_str, "%Y-%m-%d").strftime("%A")

            forecast_5day.append({
                "date":           date_str,
                "day":            day_name,
                "high_f":         high_f,
                "low_f":          low_f,
                "description":    desc,
                "rain_chance_pct":rain_chance,
                "frost_risk":     low_f < 36,
                "solar_rating":   _solar_rating(avg_clouds, rain_chance),
                "plant_risk":     _day_plant_risk(avg_humidity, low_f, rain_chance),
            })

        # ── Alerts ───────────────────────────────────────────────────────
        frost_warning   = any(d["low_f"] < 32          for d in forecast_5day[:2])
        storm_incoming  = any(d["rain_chance_pct"] > 70 for d in forecast_5day[:3])
        drought_risk    = all(d["rain_chance_pct"] < 10  for d in forecast_5day)
        disease_risk    = _overall_disease_risk(humidity, temp_f, forecast_5day)
        solar_outlook   = _solar_outlook(irradiance, forecast_5day)

        briefing = _homestead_briefing(
            temp_f, humidity, irradiance,
            frost_warning, storm_incoming, disease_risk, forecast_5day
        )

        return {
            "status":   "ok",
            "location": location,
            "current": {
                "temp_f":                  temp_f,
                "feels_like_f":            feels_like_f,
                "humidity":                humidity,
                "description":             description,
                "wind_mph":                wind_mph,
                "uv_index":                uv_index,
                "cloud_cover_pct":         cloud_cover,
                "solar_irradiance_estimate": irradiance,
            },
            "forecast_5day": forecast_5day,
            "alerts": {
                "frost_warning":      frost_warning,
                "frost_date_last":    "May 1",
                "storm_incoming":     storm_incoming,
                "drought_risk":       drought_risk,
                "plant_disease_risk": disease_risk,
                "solar_outlook":      solar_outlook,
            },
            "homestead_briefing": briefing,
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {str(e)}")
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


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


@app.get("/knowledge/{topic_id}", tags=["Knowledge Guide"])
def get_knowledge(topic_id: str):
    """Get a specific knowledge guide topic."""
    topic = KNOWLEDGE_BASE.get(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found.")
    return {"status": "ok", "topic": topic}


# ─────────────────────────────────────────────
# ADVISOR (AI CHAT)
# ─────────────────────────────────────────────

class AdvisorRequest(BaseModel):
    message: str

@app.post("/api/advisor", tags=["Advisor"])
def advisor(req: AdvisorRequest):
    """
    AI-powered off-grid advisor. Ask anything about plants, solar, or sustainable living.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Advisor unavailable: ANTHROPIC_API_KEY not set.")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=(
                "You are Vedura AI, a knowledgeable and warm off-grid living advisor for the Zen Vision platform. "
                "You help users with plant health, solar power management, sustainable living, and off-grid skills. "
                "Keep responses concise (2-4 sentences) and practical. Use plain text only — no markdown."
            ),
            messages=[{"role": "user", "content": req.message}]
        )
        reply = message.content[0].text
        return {"reply": reply}
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Advisor error: {str(e)}")


# ─────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────

def _calculate_health_score(results: dict) -> int:
    """
    Weighted health score (0-100).

    green_ratio is the primary signal — a green plant with no issues should
    score 80+. Penalties only kick in at meaningful confidence levels.

      green_ratio >= 0.82  ->  15-35 pts additive
      green_ratio >= 1.25  ->  full 35 pts (vibrant)
      base 65 + green_pts  ->  80-100 before any penalties
      yellowing            ->  up to -25 pts
      burn / spots         ->  up to -12 pts each
      light stress         ->  up to -4 pts each
      coverage             ->  up to -8 pts if plant barely visible
    """
    green_ratio = results.get("green_ratio", 1.0)
    if green_ratio >= 1.25:
        green_pts = 35.0
    elif green_ratio >= 1.0:
        green_pts = 20.0 + (green_ratio - 1.0) / 0.25 * 15.0
    elif green_ratio >= 0.82:
        green_pts = 15.0 + (green_ratio - 0.82) / 0.18 * 5.0
    elif green_ratio >= 0.6:
        green_pts = (green_ratio - 0.6) / 0.22 * 15.0
    else:
        green_pts = 0.0

    yellow_pen = results.get("yellowing_confidence", 0) * 25.0
    burn_pen   = results.get("burn_confidence",      0) * 12.0
    spots_pen  = results.get("spots_confidence",     0) * 12.0
    over_pen   = results.get("light_over_confidence", 0) * 4.0
    under_pen  = results.get("light_under_confidence", 0) * 4.0

    # Strong green ratio caps how much burn/spots can penalize
    # A truly green plant can't be severely diseased — discount ambiguous signals
    if green_ratio > 1.0:
        burn_pen  = min(burn_pen,  8.0)
        spots_pen = min(spots_pen, 8.0)
    if green_ratio >= 1.2:
        burn_pen  = min(burn_pen,  5.0)
        spots_pen = min(spots_pen, 5.0)

    coverage = results.get("vegetation_coverage", 1.0)
    coverage_pen = max(0.0, (0.12 - coverage) * 100 * 0.5) if coverage < 0.12 else 0.0
    if results.get("plant_pixel_count", 999) < 900:
        coverage_pen = min(coverage_pen + 5.0, 8.0)

    raw = 65.0 + green_pts - yellow_pen - burn_pen - spots_pen - over_pen - under_pen - coverage_pen
    score = max(0, min(100, round(raw)))

    # Floor: a genuinely green plant cannot score below 70
    if green_ratio > 1.0:
        score = max(score, 70)

    return score


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
