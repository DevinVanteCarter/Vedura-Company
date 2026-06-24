#!/usr/bin/env python3
"""
Section 9 Daily Report Generator
Calls the Anthropic API for each agent, writes reports to Obsidian vault.
"""
import anthropic
import datetime
import pathlib
import subprocess
import requests
import os

# ── Config ──────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise EnvironmentError("ANTHROPIC_API_KEY not set in environment")

VAULT = pathlib.Path.home() / "Vedura Company" / "The Vedura Company"
SECTION9 = pathlib.Path.home() / "Vedura Company" / "section9"
RAILWAY_URL = "https://zen-vision-production.up.railway.app"
CINCINNATI = datetime.date(2026, 6, 9)

AGENT_LOGS = {
    "major":    "01 - Major/Daily Log.md",
    "batou":    "02 - Batou/Task Log.md",
    "togusa":   "03 - Togusa/Intel Log.md",
    "ishikawa": "04 - Ishikawa/Metrics Log.md",
    "saito":    "05 - Saito/Copy Log.md",
    "paz":      "06 - Paz/Outreach Log.md",
    "borma":    "07 - Borma/Mycelium Log.md",
}

AGENT_FORMAT = {
    "major":    "blocked/moving/wins + top 3 priorities + Cincinnati countdown",
    "batou":    "endpoint status + any bugs found + infra health",
    "togusa":   "competitive intel update + investor targets + market signals",
    "ishikawa": "metrics update + forum signals + problem prioritization changes",
    "saito":    "content produced today + pitch material status + hook performance",
    "paz":      "outreach completed + channels engaged + user acquisition progress",
    "borma":    "Mycelium node count + harvest broadcasts + network health",
}

# ── Live context ─────────────────────────────────────────────────────────────

def get_live_context():
    ctx = {
        "health": "unknown",
        "plant_count": 0,
        "harvest_count": 0,
        "total_kg": 0.0,
        "days": (CINCINNATI - datetime.date.today()).days,
    }
    try:
        r = requests.get(f"{RAILWAY_URL}/health", timeout=8)
        ctx["health"] = "healthy" if r.status_code == 200 else f"degraded ({r.status_code})"
    except Exception as e:
        ctx["health"] = f"unreachable ({e})"

    try:
        r = requests.get(f"{RAILWAY_URL}/plants", timeout=8)
        if r.status_code == 200:
            data = r.json()
            ctx["plant_count"] = len(data) if isinstance(data, list) else data.get("count", 0)
    except Exception:
        pass

    try:
        r = requests.get(f"{RAILWAY_URL}/harvests", timeout=8)
        if r.status_code == 200:
            data = r.json()
            harvests = data if isinstance(data, list) else data.get("harvests", [])
            ctx["harvest_count"] = len(harvests)
            ctx["total_kg"] = round(sum(
                float(h.get("quantity_kg", h.get("kg", h.get("weight_kg", 0))))
                for h in harvests
                if isinstance(h, dict)
            ), 2)
    except Exception:
        pass

    return ctx

# ── Report generation ─────────────────────────────────────────────────────────

def read_soul(agent: str) -> str:
    soul_path = SECTION9 / f"SOUL_{agent}.md"
    if soul_path.exists():
        return soul_path.read_text()
    return f"You are {agent.capitalize()}, a Section 9 agent for The Vedura Company."

def build_user_message(agent: str, ctx: dict, today: str) -> str:
    return f"""Generate your daily report for {today}.

Live context:
- API status: {ctx['health']}
- Days to Cincinnati: {ctx['days']}
- Plants tracked: {ctx['plant_count']}
- Harvest entries: {ctx['harvest_count']}
- Total harvest kg: {ctx['total_kg']}

Write your daily report in your role's specific format:
- Major: blocked/moving/wins + top 3 priorities + Cincinnati countdown
- Batou: endpoint status + any bugs found + infra health
- Togusa: competitive intel update + investor targets + market signals
- Ishikawa: metrics update + forum signals + problem prioritization changes
- Saito: content produced today + pitch material status + hook performance
- Paz: outreach completed + channels engaged + user acquisition progress
- Borma: Mycelium node count + harvest broadcasts + network health

Your specific format for today: {AGENT_FORMAT[agent]}

Be specific. Use real numbers from the live context. Keep it under 200 words."""

def generate_report(client: anthropic.Anthropic, agent: str, ctx: dict, today: str) -> tuple[str, int]:
    soul = read_soul(agent)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=soul,
        messages=[{"role": "user", "content": build_user_message(agent, ctx, today)}]
    )
    text = message.content[0].text
    tokens = message.usage.input_tokens + message.usage.output_tokens
    return text, tokens

# ── Obsidian writer ───────────────────────────────────────────────────────────

def write_to_vault(agent: str, content: str, header_suffix: str = ""):
    filepath = VAULT / AGENT_LOGS[agent]
    filepath.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"## {timestamp}{header_suffix}"
    entry = f"\n{header}\n{content}\n"
    with open(filepath, "a") as f:
        f.write(entry)
    return filepath

# ── Master brief ──────────────────────────────────────────────────────────────

def generate_master_brief(client: anthropic.Anthropic, reports: dict, ctx: dict, today: str) -> tuple[str, int]:
    all_reports = "\n\n".join(
        f"=== {agent.upper()} ===\n{report}" for agent, report in reports.items()
    )
    soul = read_soul("major")
    prompt = f"""Today is {today}. Days to Cincinnati: {ctx['days']}. API: {ctx['health']}.

Here are all 7 Section 9 agent reports for today:

{all_reports}

Synthesize these into a MASTER BRIEF. Format:
- Top 3 strategic priorities right now
- What's blocked and who owns unblocking it
- Biggest win or forward motion today
- Cincinnati readiness: what's green, what's red
- One-line directive for each agent tomorrow

Keep it under 250 words. Be direct. This is your command summary."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=soul,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text
    tokens = message.usage.input_tokens + message.usage.output_tokens
    return text, tokens

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today = datetime.date.today().isoformat()
    total_tokens = 0
    reports = {}
    errors = []

    print(f"\n{'━'*50}")
    print(f"  SECTION 9 DAILY REPORT — {today}")
    print(f"{'━'*50}")

    # Live context
    print("\n[ Fetching live context... ]")
    ctx = get_live_context()
    print(f"  API:       {ctx['health']}")
    print(f"  Cincinnati: {ctx['days']} days")
    print(f"  Plants:    {ctx['plant_count']}")
    print(f"  Harvests:  {ctx['harvest_count']} entries / {ctx['total_kg']} kg")

    # Per-agent reports
    print("\n[ Generating agent reports... ]")
    for agent in AGENT_LOGS:
        try:
            report, tokens = generate_report(client, agent, ctx, today)
            reports[agent] = report
            total_tokens += tokens
            path = write_to_vault(agent, report)
            print(f"  ✓ {agent:<10} → {path.name}  ({tokens} tokens)")
        except Exception as e:
            errors.append((agent, str(e)))
            print(f"  ✗ {agent:<10} ERROR: {e}")

    # Master brief
    if reports:
        print("\n[ Generating Master Brief... ]")
        try:
            brief, tokens = generate_master_brief(client, reports, ctx, today)
            total_tokens += tokens
            path = write_to_vault("major", brief, header_suffix=" — SECTION 9 MASTER BRIEF")
            print(f"  ✓ master brief → {path.name}  ({tokens} tokens)")
        except Exception as e:
            errors.append(("master_brief", str(e)))
            print(f"  ✗ master brief ERROR: {e}")

    # Summary
    print(f"\n{'━'*50}")
    print(f"  Agents reported: {len(reports)}/7")
    print(f"  Total tokens:    {total_tokens:,}")
    if errors:
        print(f"  Errors ({len(errors)}):")
        for agent, err in errors:
            print(f"    - {agent}: {err}")
    print(f"{'━'*50}\n")

if __name__ == "__main__":
    main()
