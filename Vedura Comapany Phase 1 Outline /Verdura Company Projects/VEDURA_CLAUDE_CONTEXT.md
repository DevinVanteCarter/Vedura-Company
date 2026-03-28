# THE VEDURA COMPANY — CLAUDE CONTEXT FILE
## Upload this to your Claude Pro Project to restore full context instantly
### Last updated: March 27, 2026

---

## WHO I AM
- **Name**: Aspen Laurent
- **Location**: Loveland, Ohio
- **Company**: The Vedura Company
- **Product**: Zen Vision
- **GitHub**: github.com/AspenLaurent/zen-vision
- **Email**: aspensolenelaurent@gmail.com

---

## THE VISION
The Vedura Company is the world's first truly solarpunk technology company. We give people a real alternative to a system that has failed them — rising energy costs, fragile food supply chains, and loss of purpose. We build tools for off-grid living that are private, local-first, and community-driven.

**Tagline**: "The earth knows how to sustain us. We help you listen."
**Mission**: Bring life back into people's mornings.
**Philosophy**: Solarpunk is not an aesthetic. It's a plan.

---

## LIVE URLS (ALL WORKING)
- **Company website**: https://zen-vision-sigma.vercel.app
- **Zen Vision app**: https://zen-vision-sigma.vercel.app/app.html
- **API (Railway)**: https://zen-vision-production.up.railway.app
- **API docs**: https://zen-vision-production.up.railway.app/docs
- **GitHub**: https://github.com/AspenLaurent/zen-vision

---

## TECH STACK

### Core AI Engines (plant_health/ package)
- `image_analyzer.py` — OpenCV computer vision, HSV color analysis, Canny edge detection, spot mapping. Detects yellowing, burn, pests, light stress.
- `video_analyzer.py` — Temporal trend analysis, linear slope on green ratios over time
- `solar_ai.py` — Priority-based load routing across solar, battery, grid. Explainable decisions. SolarAIController class.

### Backend
- **FastAPI** — REST API wrapping all Zen Vision engines
- **Deployed**: Railway — zen-vision-production.up.railway.app
- **Dockerfile** — Uses python:3.11-slim with libxcb1, libgl1, libglib2.0-0, libsm6, libxext6, libxrender1, libgomp1, ffmpeg
- **Root directory on Railway**: zenvision_api/

### Frontend
- **Website**: index.html — Vedura Company marketing site
- **App**: app.html — Zen Vision demo (plant scanner + solar dashboard + AI advisor)
- **Deployed**: Vercel — zen-vision-sigma.vercel.app
- **Design**: Dark solarpunk — forest greens, earth tones, Cormorant Garamond + DM Mono typography

### AI Layer
- **Cloud AI advisor**: Groq API (llama-3.1-8b-instant) via /api/advisor.js serverless function
- **Local AI**: Ollama running llama3.1 and Mistral on Mac Studio
- **Agent**: OpenClaw — installed and configured for iMessage + session memory

### Environment Variables (Vercel)
- `GROQ_API_KEY` — Groq API key for cloud AI advisor

---

## FILE STRUCTURE
```
/Users/aspenlaurent/Vedura Company/
├── index.html                    ← Company website (live on Vercel)
├── app.html                      ← Zen Vision demo app (live on Vercel)
├── zen_vision.py                 ← Original CLI application
├── chatbot.py                    ← Ghost in the Shell chatbot
├── requirements.txt
├── README.md
├── vedura_start.sh               ← One-command startup script
├── vedura_stop.sh                ← One-command stop script
├── vedura_pitch_v3.pptx          ← Cincinnati AI Week pitch deck (12 slides)
├── vedura_master_document.docx   ← Full company bible
├── api/
│   └── advisor.js                ← Groq AI advisor serverless function
├── zenvision_api/                ← FastAPI backend
│   ├── main.py                   ← All API endpoints
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── nixpacks.toml
│   ├── Procfile
│   └── plant_health/
│       ├── __init__.py
│       ├── image_analyzer.py
│       ├── video_analyzer.py
│       ├── solar_ai.py
│       └── cli.py
└── Verdura Company Projects/
```

---

## API ENDPOINTS

### System
- `GET /` — Status check
- `GET /health` — Health check

### Plant Health
- `POST /plant/analyze/image` — Upload image, returns health_score (0-100), alerts[], raw data
- `POST /plant/analyze/video` — Upload video, returns trend (declining/stable/improving)

### Solar AI
- `GET /solar/status` — Live solar output, battery %, demand, load routing, recommendations
- `POST /solar/simulate?hours=24` — Hour-by-hour simulation
- `GET /solar/recommend` — AI power management recommendations

### Knowledge Guide
- `GET /knowledge` — List topics (solar, water, plants, battery, shelter)
- `GET /knowledge/{topic_id}` — Get specific topic

---

## LOCAL STARTUP COMMANDS

### One command to start everything:
```bash
bash '/Users/aspenlaurent/Vedura Company/vedura_start.sh'
```

### Manual sequence:
```bash
# 1. Start Ollama
OLLAMA_ORIGINS="*" OLLAMA_HOST="0.0.0.0" ollama serve

# 2. Start Zen Vision API (new terminal)
cd '/Users/aspenlaurent/Vedura Company/zenvision_api'
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 3. Start PWA server (new terminal)
cd ~/Downloads/zenvision_pwa && python3 -m http.server 3001

# 4. Start OpenClaw (new terminal)
openclaw gateway start
```

### Local access:
- Mac: http://localhost:3001/zenvision_demo.html
- iPhone (WiFi): http://192.168.4.28:3001/zenvision_demo.html
- API docs: http://localhost:8000/docs
- OpenClaw: http://127.0.0.1:18789

### Stop everything:
```bash
bash '/Users/aspenlaurent/Vedura Company/vedura_stop.sh'
```

---

## COMPETITIVE LANDSCAPE
We are the ONLY platform combining all five for the individual homesteader:

| Competitor | Plant AI | Solar AI | Local AI | Mobile | Individual |
|---|---|---|---|---|---|
| **Vedura / Zen Vision** | ✓ | ✓ | ✓ | ✓ | ✓ |
| OffGrid AI Toolkit | ✗ | ✗ | ✓ | ✗ | ✓ |
| SmartHelio | ✗ | ✓ | ✗ | ✓ | ✗ |
| Toshiba Solar AI | ✗ | ✓ | ✗ | ✓ | ✗ |
| FarmBot | ✓ | ✗ | ✗ | ✗ | ✓ |
| Tesla Powerwall | ✗ | ✓ | ✗ | ✓ | ✓ |

**Our moat**: "They can build the software. They cannot build the soul."

---

## MARKET OPPORTUNITY
- 250,000+ off-grid households in the US — growing 15% annually
- 18,000+ in Ohio alone — our home market
- Ohio + Indiana = top 5 states for off-grid growth
- Zero dominant app in the space
- $36M ARR at just 1% capture at $12/month

---

## BUSINESS MODEL
1. **Subscription app** — $9-15/month (plant scans, solar, AI, community)
2. **Hardware bundles** — $299-999 one-time (solar kits, sensors, cameras)
3. **Community & courses** — $29/month premium

**Path to profitability**: 5,000 subscribers = $600K ARR in 18 months

---

## CINCINNATI AI WEEK — JUNE 9, 2026
- **74 days away** from March 27, 2026
- **Pitch deck**: vedura_pitch_v3.pptx (12 slides)
- **Ask**: Pre-seed funding — need to lock down specific number
- **Demo**: zen-vision-sigma.vercel.app/app.html — live and working

### Roadmap:
- **Now**: Website live, API live, demo live, Groq AI working globally ✅
- **April**: Live plant camera scan, morning AI briefings, zenvision.co domain, first 10 beta users
- **May**: 100 Ohio homesteaders, community launch, App Store submission
- **June 9**: Live demo on stage, investor meetings, raise pre-seed

### Three things that win the room:
1. One real user story with a quote
2. Live demo at zen-vision-sigma.vercel.app (working NOW)
3. Specific funding ask with total confidence

---

## WHAT NEEDS TO BE BUILT NEXT
1. **Live plant camera scan** — point phone camera at plant, instant result (no file upload)
2. **Morning AI briefing** — Vedura proactively messages you daily via OpenClaw
3. **Custom domain** — zenvision.co or vedura.co
4. **React Native app** — real iOS/Android app for App Store
5. **First 100 users** — post in Ohio homesteading communities on Reddit/Facebook
6. **Lock down funding ask** — specific number for Cincinnati

---

## DEPLOYMENT NOTES

### Railway (API)
- Root directory: `zenvision_api/`
- Dockerfile handles OpenCV system dependencies
- Port: 8000
- Auto-deploys on push to main

### Vercel (Frontend)
- Framework: Other (static)
- Auto-deploys on push to main
- Environment variable: GROQ_API_KEY
- Git email must match GitHub: aspensolenelaurent@gmail.com

### GitHub
- Repo: AspenLaurent/zen-vision (private)
- Main branch: main
- Git config: user.email = aspensolenelaurent@gmail.com

---

## HOW TO USE THIS FILE WITH CLAUDE PRO
1. Create a Project called "Vedura Company"
2. Upload this file to the project
3. Add custom instruction: "I am Aspen Laurent, founder of The Vedura Company. Always read my context file before responding. I'm building Zen Vision — a solarpunk AI platform for off-grid homesteaders. We're pitching at Cincinnati AI Week on June 9, 2026."
4. Every conversation will start with full context — no need to explain anything from scratch.

---

*The Vedura Company · Zen Vision · Loveland, Ohio · 2026*
*"The exit ramp exists. We built it." 🌱☀️*
