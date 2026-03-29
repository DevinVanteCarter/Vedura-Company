# THE VEDURA COMPANY — CLAUDE PRO CONTEXT FILE v2
## Upload this to your Claude Pro Project for instant full context
### Last updated: March 28, 2026

---

## QUICK START FOR CLAUDE
When Aspen starts a conversation, you already know everything. No need to ask what the project is. Jump straight into building. Aspen is a visionary founder, not a developer — be his technical co-founder. Be direct, practical, and match his energy. He moves fast.

---

## WHO I AM
- **Name**: Aspen Laurent
- **Location**: Loveland, Ohio
- **Company**: The Vedura Company
- **Product**: Zen Vision
- **GitHub**: github.com/AspenLaurent/zen-vision
- **Email**: aspensolenelaurent@gmail.com
- **Mac**: Mac Studio (Apple Silicon) — powerful local AI machine

---

## THE VISION IN ONE PARAGRAPH
The Vedura Company is the world's first truly solarpunk technology company. We give people a real alternative to a system that has failed them — rising energy costs, fragile food supply chains, and loss of purpose. Our first product is Zen Vision — an AI platform for off-grid living combining plant health monitoring, solar power management, and a local AI advisor. Everything runs on your own hardware. Private. Free. Yours.

**Tagline**: "The earth knows how to sustain us. We help you listen."
**Mission**: Bring life back into people's mornings.
**Philosophy**: Solarpunk is not an aesthetic. It's a plan.
**Origin**: "I'm seeing people's livelihoods get turned to absolute garbage. I want to bring life back into people's lives when they wake up in the morning."

---

## LIVE URLS — ALL WORKING RIGHT NOW
| What | URL |
|------|-----|
| Company website | https://zen-vision-sigma.vercel.app |
| Zen Vision app | https://zen-vision-sigma.vercel.app/app.html |
| API (Railway) | https://zen-vision-production.up.railway.app |
| API docs | https://zen-vision-production.up.railway.app/docs |
| GitHub repo | https://github.com/AspenLaurent/zen-vision |

---

## WHAT'S FULLY BUILT AND WORKING

### Core AI Engines (plant_health/ package)
- **image_analyzer.py** — OpenCV computer vision. HSV color analysis, Canny edge detection, morphological operations, spot mapping. Detects: yellowing (nutrient deficiency), burn/browning, pests/spots, light stress (over/under exposure). Returns health_score 0-100.
- **video_analyzer.py** — Temporal trend analysis. Samples frames, runs linear slope on green ratios. Returns: declining/stable/improving trend.
- **solar_ai.py** — SolarAIController class. Priority-based load routing across solar, battery, grid. Essential loads first (Home Base, HVAC, Water Pump), non-essential deferred when grid is expensive. Explainable decisions via reroute_decision(). step() simulates one hour.

### Backend (FastAPI — Live on Railway)
- **main.py** — All endpoints. Wraps all three AI engines.
- **Deployed**: zen-vision-production.up.railway.app
- **Dockerfile**: python:3.11-slim + libxcb1, libgl1, libglib2.0-0, libsm6, libxext6, libxrender1, libgomp1, ffmpeg
- **Railway root directory**: zenvision_api/
- **Auto-deploys** on push to GitHub main branch

### Frontend (Vercel — Live)
- **index.html** — Vedura Company marketing website. Dark solarpunk design. Cormorant Garamond + DM Mono typography. Custom cursor, scroll animations, organic orb backgrounds.
- **app.html** — Zen Vision demo app. Plant scanner + solar dashboard + AI advisor.
- **Deployed**: zen-vision-sigma.vercel.app
- **Auto-deploys** on push to GitHub main branch
- **Vercel env var**: GROQ_API_KEY (for cloud AI advisor)

### AI Layer
- **Cloud AI advisor**: Groq API via /api/advisor.js serverless function. Model: llama-3.1-8b-instant. Works for anyone worldwide.
- **Local AI**: Ollama running llama3.1 + Mistral on Mac Studio. Free, private, offline capable.
- **Agent**: OpenClaw v2026.3.13 installed. Configured for iMessage + session memory. Model: llama3.1 via Ollama. Dashboard: http://127.0.0.1:18789

### Logo
- Hexagon mark + VEDURA wordmark. SVG inline in website.
- Solar arc (golden) + botanical leaf with circuit veins (green) + hexagon geometry
- Colors: forest green #1B4332, moss #52B788, sage #95D5B2, amber #FFD166, cream #F8F4E3

---

## COMPLETE FILE STRUCTURE
```
/Users/aspenlaurent/Vedura Company/
├── index.html                    ← Company website (LIVE on Vercel)
├── app.html                      ← Zen Vision demo app (LIVE on Vercel)
├── logo.svg                      ← Vedura logo mark
├── zen_vision.py                 ← Original CLI application
├── chatbot.py                    ← Ghost in the Shell chatbot (Motoko)
├── requirements.txt              ← opencv-python, numpy, scikit-image, imutils, matplotlib
├── README.md
├── vedura_start.sh               ← One-command startup script
├── vedura_stop.sh                ← One-command stop script
├── vedura_pitch_v3.pptx          ← Cincinnati AI Week pitch deck (12 slides)
├── vedura_master_document.docx   ← Full company bible
├── VEDURA_CLAUDE_CONTEXT.md      ← This file (v1)
├── api/
│   └── advisor.js                ← Groq AI advisor serverless function (Vercel)
├── zenvision_api/                ← FastAPI backend
│   ├── main.py                   ← All API endpoints
│   ├── requirements.txt          ← fastapi, uvicorn, opencv-python-headless, numpy, scikit-image
│   ├── Dockerfile                ← Railway deployment config
│   ├── nixpacks.toml             ← Railway nixpacks config
│   ├── Procfile                  ← web: uvicorn main:app
│   └── plant_health/
│       ├── __init__.py           ← version 0.1.0
│       ├── image_analyzer.py     ← Plant health computer vision
│       ├── video_analyzer.py     ← Temporal trend analysis
│       ├── solar_ai.py           ← Solar power AI controller
│       └── cli.py                ← Command line interface
└── Verdura Company Projects/     ← Additional project files
```

---

## API ENDPOINTS (all live at zen-vision-production.up.railway.app)

| Method | Endpoint | What it does |
|--------|----------|-------------|
| GET | / | Status check — returns version and message |
| GET | /health | Health check |
| POST | /plant/analyze/image | Upload image → health_score, alerts[], raw data |
| POST | /plant/analyze/video | Upload video → trend, avg_green_ratio, total_spots |
| GET | /solar/status | Live solar output, battery%, demand, load routing, recommendations |
| POST | /solar/simulate?hours=24 | Hour-by-hour power simulation |
| GET | /solar/recommend | AI power management recommendations |
| GET | /knowledge | List off-grid topics |
| GET | /knowledge/{id} | Get topic (solar/water/plants/battery/shelter) |

---

## LOCAL STARTUP

### One command (recommended):
```bash
bash '/Users/aspenlaurent/Vedura Company/vedura_start.sh'
```

### Manual sequence:
```bash
# Terminal 1 — Ollama (local AI)
OLLAMA_ORIGINS="*" OLLAMA_HOST="0.0.0.0" ollama serve

# Terminal 2 — Zen Vision API
cd '/Users/aspenlaurent/Vedura Company/zenvision_api'
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3 — PWA server
cd ~/Downloads/zenvision_pwa && python3 -m http.server 3001

# Terminal 4 — OpenClaw
openclaw gateway start
```

### Local URLs:
- Mac browser: http://localhost:3001/zenvision_demo.html
- iPhone (same WiFi): http://192.168.4.28:3001/zenvision_demo.html
- API docs: http://localhost:8000/docs
- OpenClaw: http://127.0.0.1:18789

### Stop everything:
```bash
bash '/Users/aspenlaurent/Vedura Company/vedura_stop.sh'
```

### Push to GitHub:
```bash
cd '/Users/aspenlaurent/Vedura Company'
git add .
git commit -m "your message"
git push
```
**Note**: git email must be aspensolenelaurent@gmail.com (matches GitHub)

---

## DESIGN SYSTEM
- **Colors**: --forest: #1B4332, --moss: #52B788, --sage: #95D5B2, --cream: #F8F4E3, --earth: #A3783A, --deep: #081C15, --amber: #FFD166, --muted: #8A9E92
- **Typography**: Cormorant Garamond (display/serif), DM Mono (monospace/labels), Jost (body)
- **Aesthetic**: Dark solarpunk — organic meets geometric, nature meets technology
- **Motion**: CSS scroll animations, custom cursor, glowing orb backgrounds

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

**Key moat**: "They can build the software. They cannot build the soul."

---

## MARKET OPPORTUNITY
- 250,000+ off-grid households in the US — growing 15% annually
- 18,000+ in Ohio alone — our home market
- Ohio + Indiana = top 5 states for off-grid growth
- Zero dominant app in the space — first mover advantage
- $36M ARR at just 1% capture at $12/month

---

## BUSINESS MODEL
| Stream | Price | Notes |
|--------|-------|-------|
| Subscription app | $9-15/month | Plant scans, solar, AI advisor, community |
| Hardware bundles | $299-999 one-time | Solar kits, sensors, cameras |
| Community & courses | $29/month premium | Expert Q&A, guides, peer networks |

**Path to profitability**: 5,000 subscribers = $600K ARR in 18 months

---

## CINCINNATI AI WEEK — JUNE 9, 2026
- **Days away**: ~74 days from March 28, 2026
- **Pitch deck**: vedura_pitch_v3.pptx (12 slides — best of v1 design + v2 content)
- **Live demo**: zen-vision-sigma.vercel.app/app.html — working for anyone worldwide
- **Ask**: Pre-seed funding — specific number TBD

### Pitch deck slide order:
1. Title — The world's first truly solarpunk company
2. Problem — Energy, food, purpose (three dark cards)
3. Mission — "Like Superman, I want to help" (hero quote)
4. Solution — Zen Vision with features + phone mockup
5. What we've built — 6 real working systems
6. Competitive landscape — comparison table
7. Market — $36M ARR potential
8. Business model — three revenue streams
9. Why we win — four moats
10. Roadmap — 80 days to Cincinnati
11. The ask — pre-seed funding
12. Close — "The exit ramp exists. We built it."

### Three things that win the room:
1. **One real user story** — get one person using it and quote them
2. **Live demo** — zen-vision-sigma.vercel.app/app.html works NOW
3. **Specific ask** — lock down one number with total confidence

---

## WHAT NEEDS TO BE BUILT NEXT (priority order)

### 1. Custom domain (today — $12)
- Check vedura.co or zenvision.co on namecheap.com
- Connect to Vercel for free
- Makes pitch credible — not a prototype URL

### 2. First real users (this week — free)
Post in these communities:
- r/homestead and r/OffGrid on Reddit
- Ohio Homesteaders Facebook groups
- r/solarpunk
Message: "Built a free AI tool for homesteaders — scan plants, monitor solar, ask an AI advisor. No account needed. Try it: zen-vision-sigma.vercel.app/app.html"

### 3. Live plant camera scan (1-2 days)
- Replace file upload with camera access using getUserMedia()
- Point phone camera at plant → instant health result
- The demo moment that makes people gasp

### 4. Morning AI briefing (1-2 days)
- OpenClaw cron job that runs daily at 7am
- Calls /solar/status and sends summary to iMessage
- "Good morning Aspen. Battery at 68%. Peak solar in 3 hours."

### 5. React Native app (2-4 weeks)
- Real iOS + Android app for App Store
- Needs Apple Developer account ($99/year)
- Use expo for fastest development

### 6. Lock down funding ask
- One specific number
- Breakdown: app dev + marketing + first 1,000 users + hardware partnerships
- Practice saying it until effortless

---

## DEPLOYMENT NOTES

### Railway (API backend)
- Root directory: `zenvision_api/`
- Dockerfile handles all OpenCV system dependencies
- Port: 8000 (set in Generate Domain settings)
- Auto-deploys on push to GitHub main

### Vercel (Frontend)
- Framework preset: Other (static site)
- Auto-deploys on push to GitHub main
- Environment variable: `GROQ_API_KEY`
- Git email must match GitHub: aspensolenelaurent@gmail.com

### GitHub
- Repo: AspenLaurent/zen-vision (private)
- Branch: main
- Config: `git config --global user.email "aspensolenelaurent@gmail.com"`

### Common issues & fixes
- Port 8000 already in use: `pkill -f uvicorn` then restart
- Ollama won't quit: Click llama icon in Mac menu bar → Quit
- Git blocked by Vercel: Check `git config --global user.email` matches GitHub email
- OpenCV crash on Railway: Dockerfile must include libxcb1, libgl1, libglib2.0-0

---

## WHAT WE BUILT TOGETHER (session history summary)
This entire company was built in one series of Claude conversations starting March 20, 2026:

1. Reviewed existing Zen Vision code (zen_vision.py, plant_health package)
2. Built FastAPI backend wrapping all engines
3. Installed Ollama + Mistral on Mac Studio (free local AI)
4. Set up OpenClaw AI agent with iMessage
5. Built PWA demo web app (solarpunk design)
6. Created 12-slide pitch deck (vedura_pitch_v3.pptx)
7. Deployed API to Railway (fixed OpenCV Docker issues)
8. Deployed frontend to Vercel
9. Added Groq AI advisor (works for anyone worldwide)
10. Built full Vedura Company website
11. Integrated custom SVG logo
12. Separated website (index.html) from app (app.html)
13. Created startup/stop scripts
14. Pushed everything to GitHub

**Total time**: ~3 days of building sessions
**Total cost**: $0 (Railway free tier, Vercel free, Groq free, Ollama free)

---

## HOW TO USE THIS FILE
1. In Claude Pro — create a **Project** called "Vedura Company"
2. Upload this file to the project
3. Set custom instruction:
   > "I am Aspen Laurent, founder of The Vedura Company. You are my technical co-founder. Always read my context file before responding. I'm building Zen Vision — a solarpunk AI platform for off-grid homesteaders. We're pitching at Cincinnati AI Week on June 9, 2026. I move fast, skip the pleasantries, and just build."
4. Every conversation starts fully loaded — no catching up needed

---

*The Vedura Company · Zen Vision · Loveland, Ohio · 2026*
*"The exit ramp exists. We built it." 🌱☀️*
