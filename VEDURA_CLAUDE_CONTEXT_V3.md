# THE VEDURA COMPANY — CLAUDE PRO CONTEXT FILE v3
## Upload this to your Claude Pro Project for instant full context
## Claude Code can use this to fix the Railway deployment automatically
### Last updated: March 31, 2026

---

## PRIORITY: RAILWAY API IS BROKEN — FIX THIS FIRST

### The Problem
The Railway deployment is crashing with this error:
```
the executable 'app/python=/app' could not be found
```
Or cycling between:
```
/usr/local/bin/python: No module named zenvision_api
```

### What We Know
- All Python source files have CORRECT imports (`from plant_health.x` not `from zenvision_api.plant_health.x`)
- The Dockerfile looks correct (see below)
- Railway may have a conflicting Start Command in its Settings panel
- The pycache files were deleted
- A `.gitignore` was added for `__pycache__/` and `*.pyc`
- Local imports work fine: `python3 -c "from plant_health.image_analyzer import analyze_image; print('OK')"` returns OK

### Current Dockerfile (zenvision_api/Dockerfile)
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Fix Checklist for Claude Code
1. Check Railway Settings → Start Command → must be EMPTY (Railway uses Dockerfile CMD)
2. Verify all imports in all .py files use `from plant_health.x` not `from zenvision_api.plant_health.x`
3. Delete any remaining pycache: `find zenvision_api -name "*.pyc" -delete`
4. Check requirements.txt has `opencv-python-headless` not `opencv-python`
5. Try reverting to last working git commit if all else fails: `git log --oneline -20`
6. Nuclear option: delete Railway service, redeploy fresh from GitHub

### Last Known Working State
The API was fully working before Aspen updated solar_ai.py and image_analyzer.py. The `zen_vision.py` root file had `from zenvision_api.plant_health...` imports that were later fixed. Railway may have cached the broken state.

### Target State
```
https://zen-vision-production.up.railway.app/health
→ {"status":"healthy"}

https://zen-vision-production.up.railway.app/solar/status
→ live solar data JSON
```

---

## WHO I AM
- **Name**: Aspen Laurent
- **Location**: Loveland, Ohio
- **Company**: The Vedura Company
- **Product**: Zen Vision
- **GitHub**: github.com/AspenLaurent/zen-vision (private)
- **Email**: aspensolenelaurent@gmail.com
- **Machine**: Mac Studio (Apple Silicon) — powerful local AI
- **Git config**: `git config --global user.email "aspensolenelaurent@gmail.com"`

---

## THE VISION
The Vedura Company is the world's first truly solarpunk technology company. We give people a real alternative — rising energy costs, fragile food supply chains, loss of purpose. Zen Vision combines plant health AI, solar power management, and a local AI advisor. Everything runs on your own hardware. Private. Free. Yours.

**Tagline**: "The earth knows how to sustain us. We help you listen."
**Mission**: Bring life back into people's mornings.
**Philosophy**: Solarpunk is not an aesthetic. It's a plan.
**Pitch**: "I'm seeing people's livelihoods get turned to absolute garbage. I want to bring life back into people's lives when they wake up in the morning."

---

## LIVE URLS
| What | URL | Status |
|------|-----|--------|
| Company website | https://zen-vision-sigma.vercel.app | ✅ Live |
| Zen Vision app | https://zen-vision-sigma.vercel.app/app.html | ⚠️ Broken (Railway down) |
| API (Railway) | https://zen-vision-production.up.railway.app | ❌ Crashed |
| API docs | https://zen-vision-production.up.railway.app/docs | ❌ Crashed |
| GitHub | https://github.com/AspenLaurent/zen-vision | ✅ Live |

---

## TECH STACK

### Core AI Engines (plant_health/ package)
- **image_analyzer.py** — OpenCV computer vision. HSV color analysis, Canny edge detection, morphological operations. Detects: yellowing, burn, pests/spots, light stress. Returns health_score 0-100 + alerts[].
- **video_analyzer.py** — Temporal trend analysis. Samples frames, linear slope on green ratios. Returns declining/stable/improving.
- **solar_ai.py** — SolarAIController class. Priority-based load routing. Essential loads first (Home Base 5kW, HVAC 3.5kW, Water Pump 2kW), non-essential deferred. step() simulates one hour. reroute_decision() returns explainable actions.

### Backend (FastAPI)
- **main.py** — All endpoints. Wraps all three AI engines.
- **Deployed on**: Railway — zen-vision-production.up.railway.app
- **Root directory on Railway**: zenvision_api/
- **Port**: 8000
- **Auto-deploys** on push to GitHub main

### Frontend (Vercel)
- **index.html** — Vedura Company marketing website
- **app.html** — Zen Vision demo (plant scanner + solar dashboard + AI advisor)
- **api/advisor.js** — Groq serverless function (Vercel)
- **Deployed**: zen-vision-sigma.vercel.app
- **Framework**: Other (static)
- **Env var**: GROQ_API_KEY
- **Auto-deploys** on push to GitHub main

### AI
- **Cloud**: Groq API via /api/advisor.js — llama-3.1-8b-instant — works for anyone worldwide
- **Local**: Ollama (llama3.1 + Mistral) on Mac Studio — free, private, offline
- **Agent**: OpenClaw v2026.3.13 — iMessage + session memory — dashboard: http://127.0.0.1:18789

### Logo
- SVG inline in both index.html and app.html
- Hexagon geometry + solar arc (golden #FFD166) + botanical leaf with circuit veins (moss #52B788)
- Wordmark: VEDURA in Cormorant Garamond, letter-spacing 8, cream #F8F4E3
- Tagline: OFF-GRID INTELLIGENCE in DM Mono

---

## PRODUCTS

### Zen Vision
AI platform for off-grid homesteaders — plant health scanning, solar management, local AI advisor.
- Frontend: Vercel (zen-vision-sigma.vercel.app)
- Backend: Railway API (zen-vision-production.up.railway.app) — currently broken
- AI: Groq (cloud) + Ollama on Mac Studio (local)

### BarnForge
Expert AI barndominium design assistant — floor plans, color systems, materials, 3D walkthroughs, off-grid integration. Powered by Claude (Anthropic).
- Status: In development, not yet deployed
- Lives at: `barnforge/index.html` in this repo
- API: `/api/barnforge.js` (Vercel serverless — routes to Anthropic, key stays server-side)
- Env var needed on Vercel: `ANTHROPIC_API_KEY`
- Model: `claude-sonnet-4-6`
- The natural pipeline: BarnForge designs the home → ZenVision runs on top of it once built

---

## FILE STRUCTURE
```
/Users/aspenlaurent/Vedura Company/
├── index.html                    ← Company website (LIVE)
├── app.html                      ← Zen Vision demo (broken - Railway down)
├── logo.svg                      ← Vedura SVG logo
├── zen_vision.py                 ← Original CLI (imports fixed)
├── chatbot.py                    ← Ghost in the Shell chatbot
├── requirements.txt
├── README.md
├── .gitignore                    ← __pycache__/, *.pyc, .DS_Store
├── vedura_start.sh               ← One-command startup
├── vedura_stop.sh                ← One-command stop
├── vedura_pitch_v3.pptx          ← Cincinnati pitch deck (12 slides)
├── vedura_master_document.docx   ← Company bible
├── VEDURA_CLAUDE_CONTEXT_V2.md   ← Previous context file
├── VEDURA_CLAUDE_CONTEXT_V3.md   ← This file
├── barnforge/
│   └── index.html                ← BarnForge app (IN DEVELOPMENT)
├── api/
│   ├── advisor.js                ← Groq AI advisor for Zen Vision (Vercel serverless)
│   └── barnforge.js              ← Anthropic proxy for BarnForge (Vercel serverless)
└── zenvision_api/
    ├── main.py                   ← FastAPI app
    ├── requirements.txt          ← fastapi, uvicorn, opencv-python-headless, numpy, scikit-image
    ├── Dockerfile                ← Railway deployment
    ├── nixpacks.toml             ← Railway nixpacks
    ├── .gitignore
    └── plant_health/
        ├── __init__.py
        ├── image_analyzer.py     ← Recently updated by Aspen
        ├── video_analyzer.py
        ├── solar_ai.py           ← Recently updated by Aspen
        └── cli.py
```

---

## API ENDPOINTS
| Method | Endpoint | Returns |
|--------|----------|---------|
| GET | / | name, status, version, message |
| GET | /health | {"status":"healthy"} |
| POST | /plant/analyze/image | health_score, alerts[], raw |
| POST | /plant/analyze/video | trend, avg_green_ratio, total_spots |
| GET | /solar/status | solar_output_kw, battery_charge_pct, load_routing, recommendations |
| POST | /solar/simulate?hours=24 | timeline[], total_power_distributed_kwh |
| GET | /solar/recommend | actions[], routing |
| GET | /knowledge | topics[] |
| GET | /knowledge/{id} | topic content |

---

## LOCAL STARTUP
```bash
# One command
bash '/Users/aspenlaurent/Vedura Company/vedura_start.sh'

# Manual
OLLAMA_ORIGINS="*" OLLAMA_HOST="0.0.0.0" ollama serve          # Terminal 1
cd '/Users/aspenlaurent/Vedura Company/zenvision_api'
uvicorn main:app --reload --host 0.0.0.0 --port 8000            # Terminal 2
cd ~/Downloads/zenvision_pwa && python3 -m http.server 3001     # Terminal 3
openclaw gateway start                                           # Terminal 4

# Stop
bash '/Users/aspenlaurent/Vedura Company/vedura_stop.sh'

# Deploy
cd '/Users/aspenlaurent/Vedura Company'
git add . && git commit -m "message" && git push
```

---

## COMPETITIVE LANDSCAPE (researched March 2026)
We are the ONLY platform combining all five for the individual homesteader:

| Competitor | Plant AI | Solar AI | Local AI | Mobile | Individual |
|---|---|---|---|---|---|
| **Vedura / Zen Vision** | ✓ | ✓ | ✓ | ✓ | ✓ |
| Plantix | ✓ | ✗ | ✗ | ✓ | ✗ (farmers only) |
| Agrio | ✓ | ✗ | ✗ | ✓ | ✗ (agronomists) |
| OffGrid AI Toolkit | ✗ | ✗ | ✓ | ✗ | ✓ (USB stick) |
| SmartHelio | ✗ | ✓ | ✗ | ✓ | ✗ (utility-scale) |
| Toshiba Solar AI | ✗ | ✓ | ✗ | ✓ | ✗ (industrial) |
| FarmBot | ✓ | ✗ | ✗ | ✗ | ✓ (hardware) |
| Tesla Powerwall | ✗ | ✓ | ✗ | ✓ | ✓ (expensive) |

**Key pitch line**: "Plantix has 100M users — all farmers. SmartHelio does solar AI — for utility plants. Nobody has built the integrated platform for the 250,000 households going off-grid. That's Vedura."

---

## MARKET
- 250,000+ off-grid US households — growing 15% annually
- 18,000+ in Ohio — our home market
- Ohio + Indiana = top 5 states for off-grid growth
- Zero dominant app — first mover advantage
- $36M ARR at 1% capture at $12/month

---

## BUSINESS MODEL
| Stream | Price |
|--------|-------|
| Subscription | $9-15/month |
| Hardware bundles | $299-999 one-time |
| Community & courses | $29/month premium |

5,000 subscribers = $600K ARR in 18 months

---

## CINCINNATI AI WEEK — JUNE 9, 2026
- ~70 days away
- Pitch deck: vedura_pitch_v3.pptx (12 slides)
- Live demo: zen-vision-sigma.vercel.app/app.html (needs Railway fixed first)
- Ask: Pre-seed — specific number TBD

### Three things that win the room:
1. One real user story with a quote
2. Live demo working on anyone's phone
3. Specific funding ask said with total confidence

### Roadmap:
- **Now**: Fix Railway ← PRIORITY
- **This week**: Get custom domain (vedura.co or zenvision.co on Namecheap ~$12)
- **This week**: Post in Ohio homesteading communities — get first 10 users
- **April**: Live camera plant scan (getUserMedia API), morning AI briefing via OpenClaw
- **May**: 100 Ohio homesteaders, App Store submission
- **June 9**: Win Cincinnati

---

## WHAT CLAUDE CODE CAN DO
Claude Code runs in your terminal and can directly edit files, run commands, push to GitHub, and fix deployment issues. When you have Claude Pro:

1. Open Terminal in your Vedura Company folder
2. Run: `claude` to start Claude Code
3. Say: "Read VEDURA_CLAUDE_CONTEXT_V3.md and fix the Railway deployment"

Claude Code will:
- Check all import paths
- Fix any remaining issues
- Update the Dockerfile if needed
- Push the fix to GitHub
- Watch Railway redeploy

---

## DESIGN SYSTEM
- **Colors**: forest #1B4332, moss #52B788, sage #95D5B2, cream #F8F4E3, earth #A3783A, deep #081C15, amber #FFD166
- **Fonts**: Cormorant Garamond (display), DM Mono (mono/labels), Jost (body)
- **Aesthetic**: Dark solarpunk — organic meets geometric
- **Motion**: CSS scroll animations, custom cursor, orb backgrounds

---

## FULL SESSION HISTORY (built March 20-31, 2026)
1. Reviewed Zen Vision code (zen_vision.py, plant_health package)
2. Built FastAPI backend wrapping all engines
3. Installed Ollama + Mistral on Mac Studio
4. Set up OpenClaw AI agent with iMessage
5. Built PWA demo web app
6. Created 12-slide pitch deck (vedura_pitch_v3.pptx)
7. Researched competitive landscape
8. Deployed API to Railway (fought OpenCV Docker issues)
9. Deployed frontend to Vercel
10. Added Groq AI advisor (works worldwide)
11. Built full Vedura Company website with solarpunk design
12. Integrated custom SVG logo (hexagon + leaf + solar arc)
13. Separated website (index.html) from app (app.html)
14. Created startup/stop scripts
15. Pushed everything to GitHub
16. Railway started crashing after Aspen updated AI files
17. Fixed import paths but Railway still broken
18. Researched competitors — confirmed gap is real and growing

**Total cost so far**: $0 (all free tiers)
**Days until Cincinnati**: ~70

---

## HOW TO USE THIS FILE
1. Claude Pro → New Project → "Vedura Company"
2. Upload this file
3. Custom instruction:
   > "I am Aspen Laurent, founder of The Vedura Company in Loveland Ohio. You are my technical co-founder. Read my context file before every response. We're building Zen Vision — solarpunk AI for off-grid homesteaders. Pitching Cincinnati AI Week June 9 2026. First priority: fix Railway deployment. Move fast, skip pleasantries, just build."

---

*The Vedura Company · Zen Vision · Loveland, Ohio · 2026*
*"The exit ramp exists. We built it." 🌱☀️*
