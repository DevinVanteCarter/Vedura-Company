# The Vedura Company — Claude Code Context

**Founder**: Aspen Laurent — Loveland, Ohio
**Mission**: The world's first solarpunk technology company. Intelligent, resilient, off-grid living.
**Tagline**: "The earth knows how to sustain us. We help you listen."
**Pitch event**: Cincinnati AI Week — June 9, 2026

---

## Products

### Zen Vision (main product)
AI platform for off-grid homesteaders — plant health scanning, solar management, local AI advisor.
- **Frontend**: Vercel → `zen-vision-sigma.vercel.app`
- **App**: `zen-vision-sigma.vercel.app/app.html`
- **Backend**: Railway → `zen-vision-production.up.railway.app` — **currently broken**
- **AI (cloud)**: Groq via `/api/advisor.js` — `llama-3.1-8b-instant`
- **AI (local)**: Ollama on Mac Studio — llama3.1 + Mistral
- **Agent**: OpenClaw v2026.3.13 — iMessage + session memory

### BarnForge (in development)
Expert AI barndominium design assistant — floor plans, color systems, 3D walkthroughs, off-grid integration.
- **Status**: In development, not yet deployed
- **File**: `barnforge/index.html`
- **API**: `api/barnforge.js` (Vercel serverless → Anthropic)
- **Model**: `claude-sonnet-4-6`
- **Env var needed**: `ANTHROPIC_API_KEY` on Vercel (not yet added)
- **Pipeline**: BarnForge designs the home → ZenVision runs on top once it's built

---

## Repo Structure
```
/
├── index.html          ← Vedura website (LIVE)
├── app.html            ← Zen Vision demo (LIVE — Railway working)
├── barnforge/
│   └── index.html      ← BarnForge app (LIVE on Vercel — needs ANTHROPIC_API_KEY on Vercel)
├── api/
│   ├── advisor.js      ← Zen Vision AI advisor (Groq)
│   └── barnforge.js    ← BarnForge AI proxy (Anthropic)
├── zenvision_api/      ← FastAPI backend (Railway — LIVE ✅)
│   ├── main.py
│   ├── Dockerfile
│   └── plant_health/
│       ├── image_analyzer.py
│       ├── video_analyzer.py
│       └── solar_ai.py
├── section9/           ← OpenClaw agent soul files
└── VEDURA_CLAUDE_CONTEXT_V3.md  ← Full company context
```

---

## Deployment
| What | Where | Status |
|------|-------|--------|
| Website + BarnForge | Vercel (auto-deploys on push) | ✅ |
| Zen Vision backend | Railway (auto-deploys on push) | ✅ Live |
| GitHub | github.com/AspenLaurent/zen-vision | ✅ |

**Deploy**: `git add . && git commit -m "message" && git push`

---

## Env Vars
| Var | Used by | Where | Status |
|-----|---------|-------|--------|
| `GROQ_API_KEY` | `/api/advisor.js` | Vercel | ✅ Set |
| `ANTHROPIC_API_KEY` | `/api/barnforge.js` | Vercel | ❌ Not yet added — BarnForge AI won't work |
| `ANTHROPIC_API_KEY` | `zenvision_api/main.py` (advisor, morning-brief, species scan) | Railway | ✅ Set |

---

## Design System
- **Colors**: forest `#1B4332`, moss `#52B788`, sage `#95D5B2`, cream `#F8F4E3`, earth `#A3783A`, deep `#081C15`, amber `#FFD166`
- **Fonts**: Cormorant Garamond (display), DM Mono (mono/labels), Jost (body)
- **Aesthetic**: Dark solarpunk — organic meets geometric
- **BarnForge aesthetic**: Dark terminal/cyberpunk — Orbitron + Share Tech Mono + Rajdhani

---

## Local Dev
```bash
# Start everything
bash '/Users/aspenlaurent/Vedura Company/vedura_start.sh'

# Stop everything
bash '/Users/aspenlaurent/Vedura Company/vedura_stop.sh'
```
