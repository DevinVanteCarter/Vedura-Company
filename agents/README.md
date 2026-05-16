# Vedura Agent Crew — SOUL Files

OpenClaw-compatible AI agent definitions for a multi-agent startup operations team.

Each agent runs on Claude Sonnet via [OpenClaw](https://openclaw.ai). These SOUL files define who each agent is, what they own, how they think, and how they log to shared memory.

---

## The Crew

| Agent | Role | Owns |
|-------|------|------|
| **Axis** | Strategic orchestrator | Scale system, daily brief, delegation |
| **Weld** | Infrastructure | API uptime, deploys, QA checklist |
| **Lens** | Research & intel | Competitor map, investor targets |
| **Tide** | Data & metrics | Problem prioritization, metric tracking |
| **Grain** | Communications | Offer, pitch, content, brand voice |
| **Bloom** | Distribution | User acquisition, community outreach |
| **Myco** | Network | Mycelium node growth, community ops |

---

## How It Works

1. Each agent has a SOUL file defining identity, mission, and specific responsibilities
2. All agents log to a shared event log via `log_event.py`
3. Events build a knowledge graph of investors, users, communities, and signals
4. Axis synthesizes logs into a daily brief sent to the founder each morning
5. Agents coordinate via Axis — Bloom surfaces a user → Tide logs the metric → Grain builds the testimonial → Axis reports progress

---

## Logging System

Every meaningful action gets logged with:
- `--agent [name]` — who logged it
- `--type [event_type]` — what happened
- `--content "..."` — what actually occurred
- `--entities "..."` — what/who is involved
- `--importance [1-10]` — signal vs noise filter
- `--goal [pitch|arr|users|ops]` — which objective this serves

Events with importance < 4 are not logged. This keeps the log clean and signal-dense.

---

## Adapting This to Your Startup

1. Replace the market context in each SOUL with your product's specifics
2. Adjust the goal tags to match your current phase priorities
3. Point `log_event.py` at your own SQLite or Supabase instance
4. Load each SOUL into an OpenClaw agent slot

The structure scales from solo founder to small team — each agent can be a Claude instance, a human, or both.

---

*The Vedura Company · Loveland, Ohio · 2026*
*"The earth knows how to sustain us. We help you listen."*
