# THE VEDURA COMPANY — CLAUDE PRO CONTEXT FILE v4
## Upload this to your Claude Pro Project for instant full context
### Last updated: June 1, 2026

---

## WHO I AM
- **Name**: Aspen Laurent
- **Location**: Loveland, Ohio
- **Company**: The Vedura Company
- **Products**: Zen Vision · BarnForge · Green Scheduler
- **GitHub**: github.com/AspenLaurent/zen-vision (private)
- **Email**: aspensolenelaurent@gmail.com
- **Machine**: Mac Studio (Apple Silicon) — powerful local AI
- **Git config**: `git config --global user.email "aspensolenelaurent@gmail.com"`

---

## THE VISION
The Vedura Company is the world's first truly solarpunk technology company. We give people a real alternative — rising energy costs, fragile food supply chains, loss of purpose. Our platform combines plant health AI, solar power management, carbon-aware compute scheduling, and a local AI advisor. Everything runs on your own hardware. Private. Resilient. Yours.

**Tagline**: "The earth knows how to sustain us. We help you listen."
**Mission**: Bring life back into people's mornings.
**Philosophy**: Solarpunk is not an aesthetic. It's a plan.
**Pitch**: "I'm seeing people's livelihoods get turned to absolute garbage. I want to bring life back into people's lives when they wake up in the morning."

---

## LIVE URLS
| What | URL | Status |
|------|-----|--------|
| Company website | https://zen-vision-sigma.vercel.app | ✅ Live |
| Zen Vision app | https://zen-vision-sigma.vercel.app/app.html | ✅ Live |
| Green Scheduler | https://zen-vision-sigma.vercel.app/scheduler.html | ✅ Live |
| BarnForge | https://zen-vision-sigma.vercel.app/barnforge/ | ✅ Live (AI enabled) |
| API (Railway) | https://zen-vision-production.up.railway.app | ✅ Live |
| API docs | https://zen-vision-production.up.railway.app/docs | ✅ Live |
| GitHub | https://github.com/AspenLaurent/zen-vision | ✅ Live |

**Domain note**: Targeting theveduracompany.com as canonical domain. Currently on Vercel subdomain.

---

## TECH STACK

### Core AI Engines (zenvision_api/plant_health/ package)
- **image_analyzer.py** — OpenCV + ONNX MobileNetV2 (PlantVillage, 38 disease classes). HSV color analysis, Canny edge detection, morphological ops. Returns health_score 0-100 + alerts[].
- **video_analyzer.py** — Temporal trend analysis. Samples frames, linear slope on green ratios. Returns declining/stable/improving.
- **solar_ai.py** — SolarAIController class. Priority-based load routing. Essential loads first (Home Base 5kW, HVAC 3.5kW, Water Pump 2kW), non-essential deferred.

### Backend (FastAPI on Railway)
- **main.py** — All endpoints. Wraps all three AI engines + Claude Haiku species ID + Claude advisor/morning-brief.
- **Deployed on**: Railway — zen-vision-production.up.railway.app
- **Root directory on Railway**: zenvision_api/
- **Port**: 8000
- **Auto-deploys** on push to GitHub main
- **Status**: LIVE ✅

### Frontend (Vercel)
- **index.html** — Vedura Company marketing website with all 6 capability cards
- **app.html** — Zen Vision demo (plant scanner + solar + advisor + homestead + mycelium + barnforge)
- **scheduler.html** — Green Scheduler (carbon-aware job routing via Claude Sonnet)
- **barnforge/index.html** — BarnForge AI design assistant
- **api/advisor.js** — Groq serverless function (Vercel) — llama-3.1-8b-instant
- **api/barnforge.js** — Anthropic proxy (Vercel) — claude-sonnet-4-6 — used by both BarnForge AND the Green Scheduler
- **Deployed**: zen-vision-sigma.vercel.app
- **Auto-deploys** on push to GitHub main

### AI
- **Plant vision**: ONNX MobileNetV2 on Railway — PlantVillage 38 classes
- **Species ID**: Claude Haiku (claude-haiku-4-5-20251001) via Railway — identifies plant species from images
- **Advisor**: Claude (via ANTHROPIC_API_KEY on Railway) — homestead AI advisor + morning brief
- **BarnForge**: Claude Sonnet (claude-sonnet-4-6) via Vercel serverless (/api/barnforge.js)
- **Green Scheduler**: Claude Sonnet (claude-sonnet-4-6) via same /api/barnforge proxy — reasoning engine for carbon-aware job routing
- **Cloud fallback**: Groq API via /api/advisor.js — llama-3.1-8b-instant
- **Local**: Ollama (llama3.1 + Mistral) on Mac Studio — free, private, offline
- **Agent**: OpenClaw v2026.3.13 — iMessage + session memory — dashboard: http://127.0.0.1:18789

### Env Vars
| Var | Where | Status |
|-----|-------|--------|
| `ANTHROPIC_API_KEY` | Railway | ✅ Set |
| `ANTHROPIC_API_KEY` | Vercel | ✅ Set (added May 16) |
| `GROQ_API_KEY` | Vercel | ✅ Set |

---

## PRODUCTS

### 1. Zen Vision (flagship)
AI platform for off-grid homesteaders. Six integrated modules:
- **Plant Scanner** — Upload or live camera. ONNX model + Claude Haiku species ID. Health score 0-100, disease detection, treatment protocols.
- **Solar Dashboard** — Live sim + NREL real data. Monthly chart, bar metrics, geo-aware.
- **AI Advisor** — Claude-powered homestead Q&A. Context-aware, private, no data retention.
- **Homestead Intelligence** — Weather engine, 5-day forecast, crop calendars, solar irradiance, priority action list.
- **Mycelium Network** — Grow tracker, harvest logger, animated grower network canvas.
- **BarnForge** — Embedded iframe to BarnForge designer.

Frontend: zen-vision-sigma.vercel.app/app.html
Backend: zen-vision-production.up.railway.app
Status: LIVE ✅ — fully audited May 16, mobile nav fixed, all features operational

### 2. BarnForge
Expert AI barndominium design assistant. Dark terminal/cyberpunk aesthetic.
- Floor plans, color systems, materials, 3D walkthroughs, off-grid integration
- Powered by Claude Sonnet (claude-sonnet-4-6) via /api/barnforge.js
- The pipeline: BarnForge designs the home → ZenVision runs on top once built
- Status: LIVE ✅ (ANTHROPIC_API_KEY set on Vercel — AI fully functional)

### 3. Green Scheduler ← NEW (built May 16, 2026)
Carbon-aware job scheduling for AI workloads. The same intelligence that manages your solar array decides when your GPU runs.
- **What it does**: Routes AI training runs, batch inference, and data pipelines to low-carbon, low-cost grid windows
- **How**: Real-time carbon intensity grid data (mock for MVP) → Claude Sonnet reasons over current conditions → outputs priority-ordered job queue with timing rationale
- **Claude's role**: Live reasoning engine — analyzes the grid state, energy mix, job priorities, and delivers an explainable schedule in natural language
- **UI**: Carbon timeline chart (24-hr), live job queue, status pills (QUEUED/RUNNING/PAUSED/SCHEDULED), Claude analysis panel
- **Design**: Matches full Vedura design system (particle canvas, scan lines, glitch nav, tower scan)
- **API**: Calls /api/barnforge proxy → claude-sonnet-4-6
- **Nav**: Listed as 06/GRID INTELLIGENCE in index.html capability card
- **Status**: LIVE ✅ at zen-vision-sigma.vercel.app/scheduler.html

---

## FILE STRUCTURE
```
/Users/aspenlaurent/Vedura Company/
├── index.html                    ← Company website (LIVE) — 6 capability cards
├── app.html                      ← Zen Vision demo (LIVE — fully audited May 16)
├── scheduler.html                ← Green Scheduler (LIVE — added May 16)
├── logo.svg                      ← Vedura SVG logo
├── CLAUDE.md                     ← Claude Code project context (auto-loaded)
├── VEDURA_CLAUDE_CONTEXT_V3.md   ← Previous context file
├── VEDURA_CLAUDE_CONTEXT_V4.md   ← This file
├── vedura_start.sh               ← One-command startup
├── vedura_stop.sh                ← One-command stop
├── vedura_pitch_v3.pptx          ← Cincinnati pitch deck (12 slides)
├── vedura_master_document.docx   ← Company bible
├── barnforge/
│   └── index.html                ← BarnForge app (LIVE — AI enabled)
├── api/
│   ├── advisor.js                ← Groq AI advisor (Vercel serverless)
│   └── barnforge.js              ← Anthropic proxy — used by BarnForge + Scheduler
└── zenvision_api/
    ├── main.py                   ← FastAPI app (LIVE on Railway)
    ├── requirements.txt
    ├── Dockerfile
    ├── nixpacks.toml
    └── plant_health/
        ├── image_analyzer.py
        ├── video_analyzer.py
        ├── solar_ai.py
        └── cli.py
```

---

## API ENDPOINTS (all live at zen-vision-production.up.railway.app)
| Method | Endpoint | Returns |
|--------|----------|---------|
| GET | /health | {"status":"healthy"} |
| GET | /debug | model_available, onnx_file_exists |
| POST | /plant/analyze/image | health_score, alerts[], raw (species, disease, treatment) |
| POST | /plant/analyze/video | trend, avg_green_ratio, total_spots |
| GET | /solar/status | solar_output_kw, battery_charge_pct, recommendations |
| GET | /solar/real | NREL real data — monthly_kwh[], annual_kwh, location |
| GET | /homestead | weather_summary, crop_data, priority_actions, connections |
| POST | /advisor | homestead AI advisor response |
| POST | /advisor/morning-brief | daily homestead briefing |
| GET | /plants | tracked plants list |
| POST | /plants | add plant |
| GET | /harvests | harvest log |
| POST | /harvests | log harvest |

---

## LOCAL STARTUP
```bash
# One command
bash '/Users/aspenlaurent/Vedura Company/vedura_start.sh'

# Deploy
cd '/Users/aspenlaurent/Vedura Company'
git add . && git commit -m "message" && git push
```

---

## COMPETITIVE LANDSCAPE (updated May 2026)

### The Real Competitors (confirmed live)
- **OffGrid AI Toolkit** — offgridaitoolkit.com — local AI on a USB stick. Privacy-first, offline. No plant health, no solar integration. Our positioning: we do everything they do + plant + solar + beautiful UI.
- **Off Grid** (mobile app) — released February 2026 — focused on off-grid lifestyle content and community. Not AI-native, not diagnostic. Our positioning: we're a tool, not a content feed.

### The Broader Landscape
| Competitor | Plant AI | Solar AI | Carbon Scheduling | Local AI | Individual |
|---|---|---|---|---|---|
| **Vedura** | ✓ | ✓ | ✓ | ✓ | ✓ |
| Plantix | ✓ | ✗ | ✗ | ✗ | ✗ (farmers only) |
| Agrio | ✓ | ✗ | ✗ | ✗ | ✗ (agronomists) |
| OffGrid AI Toolkit | ✗ | ✗ | ✗ | ✓ | ✓ |
| SmartHelio | ✗ | ✓ | ✗ | ✗ | ✗ (utility) |
| Tesla Powerwall | ✗ | ✓ | ✗ | ✗ | ✓ (expensive) |
| WattTime / ElectricityMaps | ✗ | ✗ | ✓ | ✗ | ✗ (API only) |

**Key pitch line**: "Plantix has 100M users — all farmers. OffGrid AI Toolkit gives you a USB stick but no plant scanner, no solar, no advisor. Nobody has built the integrated platform for the person going off-grid at home. That's Vedura."

---

## MARKET
- 250,000+ off-grid US households — growing 15% annually
- 18,000+ in Ohio — our home market
- Ohio + Indiana = top 5 states for off-grid growth
- Zero dominant integrated platform — first mover advantage
- $36M ARR at 1% capture at $12/month

---

## BUSINESS MODEL
| Stream | Price | Notes |
|--------|-------|-------|
| Zen Vision subscription | $9–15/month | Core homestead platform |
| Green Scheduler | $4/month add-on OR $29/month B2B | See pricing debate below |
| Hardware bundles | $299–999 one-time | Future |
| Community & courses | $29/month premium | Future |

**5,000 subscribers = $600K ARR in 18 months**

---

## CINCINNATI AI WEEK — JUNE 9, 2026
**8 days away — June 9, 2026**

- Pitch deck: vedura_pitch_v3.pptx (12 slides — needs update for Green Scheduler)
- Live demo: zen-vision-sigma.vercel.app/app.html + scheduler.html (both LIVE)
- Ask: Pre-seed — specific number TBD

### Three things that win the room:
1. One real user story with a quote
2. **Live demo working on someone else's phone** — hand it to an audience member, watch them use it cold
3. Specific funding ask said with total confidence

---

## PITCH Q&A — HARD QUESTIONS TO PREPARE FOR

### "Who is your first customer?"
**Have a real answer.** Not a persona. A name, a city, a story. Something like:
> "Sarah, homesteader outside Columbus. Her tomatoes kept dying and she didn't know why. She uploaded a photo, Vedura identified early blight in 8 seconds, gave her a neem oil protocol. She messaged me to say it was the first time her phone felt like it was actually working for her."

If you don't have one yet — get one before June 9. Post in Ohio homesteading Facebook groups this week.

### "Why not just use ChatGPT?"
ChatGPT doesn't know your solar output right now. It can't scan your plant and tell you it has early blight. It doesn't know your local frost date. Vedura is integrated with your actual homestead — live data, live sensors, your grow history. ChatGPT is a search engine that talks. Vedura is a system that knows your land.

### "Green Scheduler — is this B2C or B2B?"
Both models exist and you should pick one to lead with:
- **B2C**: $4/month add-on for homesteaders running local AI (Ollama, Stable Diffusion). "Schedule your GPU work during off-peak solar hours." Relatable. Small TAM.
- **B2B**: $29–99/month for small AI labs, freelance ML engineers, startups running batch inference. "Cut your GPU cloud bill by routing to low-carbon windows." Larger TAM, harder to sell.
- **Pitch answer**: Lead with B2C (it's authentic to the brand), acknowledge B2B upside. "Our homesteaders are already running local AI. The scheduler is what ties the whole energy picture together. The B2B play comes later — same engine, different customer."

### "Isn't $4/month too low?"
Probably yes. Options:
- Bundle it into the base subscription (no separate line item — cleaner)
- Price it as $9–12/month standalone
- Make it a premium tier: Zen Vision Pro at $19/month includes scheduler
- For B2B, $49–99/month per seat with usage-based overage

### "What's your moat?"
Three things: (1) Integration — no one else combines plant + solar + AI scheduling in one platform. (2) Local-first — we work offline, competitors don't. (3) Brand — solarpunk resonates with a growing cultural movement; this is a lifestyle product, not just a utility app.

### "What happens when Google/Apple builds this?"
Same thing that happened when Google built Maps — the local guide networks (AllTrails, iNaturalist) still win. Community, trust, and specificity to the homesteader lifestyle are things Big Tech doesn't have. Our users don't want Google knowing their solar output.

---

## DEMO SCRIPT (June 9)
1. Open zen-vision-sigma.vercel.app/app.html on audience member's phone
2. Ask them to photograph any plant in the room
3. Upload → watch score + species ID appear
4. Switch to Homestead tab → show live weather + crop calendar
5. Switch to Scheduler tab → "this is the same intelligence that runs on your solar array, now deciding when your AI workloads run"
6. Close with: "BarnForge designs the home. Zen Vision runs it. The Scheduler powers it intelligently."

---

## DESIGN SYSTEM
- **Colors**: forest #1B4332, moss #52B788, sage #95D5B2, cream #F8F4E3, earth #A3783A, deep #081C15, amber #FFD166
- **Fonts**: Cormorant Garamond (display), Share Tech Mono / DM Mono (mono/labels), Jost (body)
- **Aesthetic**: Dark solarpunk — organic meets geometric
- **Motion**: Particle canvas, scan lines, tower scan animation, glitch cursor, glitch nav logo
- **BarnForge aesthetic**: Dark terminal/cyberpunk — Orbitron + Share Tech Mono + Rajdhani

---

## FULL SESSION HISTORY

### March 20–31, 2026
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

### April 13, 2026
14. Full agent SOUL sync — OpenClaw heartbeats, brain graph nodes, Obsidian logs
15. Section 9 daily Obsidian report script
16. Section 9 brain graph visual frontend
17. Fixed plant scanner scoring, homestead auto-load, mycelium nav tab

### May 16, 2026
18. Fixed Railway API (confirmed LIVE — all endpoints healthy, ONNX model loaded)
19. Added ANTHROPIC_API_KEY to Vercel → BarnForge AI now fully functional
20. Built **Green Scheduler** (scheduler.html) — carbon-aware job routing, Claude Sonnet as reasoning engine
21. Added Green Scheduler nav link + 06/GRID INTELLIGENCE capability card to index.html
22. Restyled scheduler.html to match full Vedura design system
23. Comprehensive app.html audit — confirmed all features working
24. Fixed mobile navigation (hamburger menu at ≤700px)
25. Fixed homestead 30-minute cache (was reloading on every tab visit)

**Total cost so far**: ~$0 (all free tiers — Vercel, Railway hobby, Groq free, Anthropic API pay-per-use)
**Days until Cincinnati**: 8 (June 9, 2026)

---

## IMMEDIATE PRIORITIES (before June 9)

| Priority | Task | Status |
|----------|------|--------|
| 🔴 CRITICAL | Get one real named user with a story | Not done |
| 🔴 CRITICAL | Nail the funding ask number | TBD |
| 🔴 CRITICAL | Update pitch deck to include Green Scheduler | Needed |
| 🟡 HIGH | Get custom domain (theveduracompany.com) | TBD |
| 🟡 HIGH | Post in Ohio homesteading communities | TBD |
| 🟡 HIGH | Practice demo on someone else's phone cold | TBD |
| 🟢 READY | Zen Vision app — fully live and audited | ✅ Done |
| 🟢 READY | BarnForge — AI enabled and live | ✅ Done |
| 🟢 READY | Green Scheduler — live with Claude reasoning | ✅ Done |
| 🟢 READY | Mobile navigation — works on phones | ✅ Done |

---

## HOW TO USE THIS FILE
1. Claude Pro → Open "Vedura Company" Project
2. Upload VEDURA_CLAUDE_CONTEXT_V4.md
3. Custom instruction:
   > "I am Aspen Laurent, founder of The Vedura Company in Loveland Ohio. You are my technical co-founder. Read my context file before every response. We're building Zen Vision + BarnForge + Green Scheduler — solarpunk AI for off-grid homesteaders. Pitching Cincinnati AI Week June 9 2026 — 24 days away. Move fast, skip pleasantries, just build."

---

*The Vedura Company · Zen Vision · BarnForge · Green Scheduler · Loveland, Ohio · 2026*
*"The earth knows how to sustain us. We help you listen." 🌱☀️*
