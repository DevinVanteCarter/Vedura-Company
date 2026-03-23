# 🌱☀️ Zen Vision API

Solarpunk off-grid intelligence platform.  
Plant health + Solar AI + Knowledge guide — all in one API.

## Quick start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn main:app --reload --port 8000
```

Then open: http://localhost:8000/docs

## Endpoints

### System
- `GET /` — API info
- `GET /health` — Health check

### Plant Health
- `POST /plant/analyze/image` — Upload a plant photo, get health report
- `POST /plant/analyze/video` — Upload a plant video, get trend analysis

### Solar AI
- `GET /solar/status` — Current solar system status + load routing
- `POST /solar/simulate?hours=24` — Run an hour-by-hour simulation
- `GET /solar/recommend` — Get AI power management recommendations

### Knowledge Guide
- `GET /knowledge` — List all off-grid knowledge topics
- `GET /knowledge/{topic_id}` — Get a specific topic

## Project structure

```
zenvision_api/
├── main.py              ← FastAPI app (this file)
├── requirements.txt
├── plant_health/
│   ├── __init__.py
│   ├── image_analyzer.py
│   ├── video_analyzer.py
│   └── solar_ai.py
```

## Connecting Ollama (local AI)

Add this to main.py to connect your local Ollama model:

```python
import httpx

async def ask_ollama(prompt: str, model: str = "llama3.1") -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:11434/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False
        })
        return r.json()["response"]
```

Then wire it into any endpoint for natural language advice.

## Built with love for the off-grid community 🌿
