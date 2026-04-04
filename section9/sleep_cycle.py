"""
Section 9 — Sleep Cycle
Runs as a cron job at 3AM.
For each agent:
  - reads last 24 hrs of memory
  - prunes anything below importance 4 from the DB
  - surfaces importance >= 7 to brief (Cincinnati >= 6 auto-promoted)
  - writes ~/.openclaw/queue/{agent}_brief.json

Also writes ~/.openclaw/queue/morning_brief.json — Major's aggregated
view of all 7 agents, grouped by goal: CINCINNATI → ARR → USERS → OPS

Cron entry (add with: crontab -e):
    0 3 * * * /usr/bin/python3 "/Users/aspenlaurent/Vedura Company/section9/sleep_cycle.py"
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from section9.agent_memory import (  # noqa: E402
    AGENTS,
    _get_conn,
    delete_below_importance,
)

QUEUE_DIR = Path.home() / ".openclaw" / "queue"

# Goal display order and labels for the morning brief
GOAL_ORDER = ["cincinnati", "arr", "users", "ops", None]
GOAL_LABELS = {
    "cincinnati": "CINCINNATI",
    "arr":        "$1M ARR",
    "users":      "USERS",
    "ops":        "OPS",
    None:         "GENERAL",
}

# Thresholds
PRUNE_BELOW          = 4   # remove from DB entirely
BRIEF_MIN_IMPORTANCE = 7   # surface to brief
CINCINNATI_MIN       = 6   # lower bar for Cincinnati events (always priority)


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def _events_last_24h(agent_id: str) -> list[dict]:
    """Return all events from the last 24 hours for an agent."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT * FROM memory
        WHERE agent_id = ? AND timestamp >= ?
        ORDER BY importance DESC, timestamp DESC
        """,
        (agent_id, cutoff),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _should_surface(event: dict) -> bool:
    """
    Determine whether an event should appear in the brief.
    Rules:
      - importance >= 7 always surfaces
      - Cincinnati goal_tag + importance >= 6 auto-promotes
    """
    imp  = event.get("importance", 0)
    goal = event.get("goal_tag")
    if imp >= BRIEF_MIN_IMPORTANCE:
        return True
    if goal == "cincinnati" and imp >= CINCINNATI_MIN:
        return True
    return False


def _score_events(events: list[dict]) -> list[dict]:
    """Return surfaceable events sorted by importance desc, timestamp desc."""
    surfaced = [e for e in events if _should_surface(e)]
    return sorted(surfaced, key=lambda e: (e["importance"], e["timestamp"]), reverse=True)


def _extract_highlights(events: list[dict], max_highlights: int = 5) -> list[str]:
    lines = []
    for e in events[:max_highlights]:
        label = GOAL_LABELS.get(e.get("goal_tag"), "GENERAL")
        promoted = ""
        if e.get("goal_tag") == "cincinnati" and e.get("importance", 0) < BRIEF_MIN_IMPORTANCE:
            promoted = " [promoted]"
        lines.append(f"[{label}{promoted}] {e['event_type']}: {e['content']}")
    return lines


def _extract_action_items(events: list[dict]) -> list[str]:
    """Events with importance >= 8 become action items."""
    return [
        f"[{e['agent_id'].upper()}] {e['content']}"
        for e in events
        if e.get("importance", 0) >= 8
    ]


def _extract_goal_tags(events: list[dict]) -> list[str]:
    seen = set()
    for e in events:
        tag = e.get("goal_tag")
        if tag:
            seen.add(tag)
    return sorted(seen, key=lambda t: GOAL_ORDER.index(t) if t in GOAL_ORDER else 99)


def _build_agent_brief(agent_id: str, date_str: str) -> dict:
    all_events  = _events_last_24h(agent_id)
    scored      = _score_events(all_events)

    return {
        "agent":           agent_id,
        "date":            date_str,
        "total_events":    len(all_events),
        "retained_events": len(scored),
        "pruned_events":   len(all_events) - len(scored),
        "highlights":      _extract_highlights(scored),
        "action_items":    _extract_action_items(scored),
        "goal_tags":       _extract_goal_tags(scored),
    }


# ---------------------------------------------------------------------------
# Morning brief — grouped by goal
# ---------------------------------------------------------------------------

def _build_morning_brief(agent_briefs: dict[str, dict], date_str: str) -> dict:
    """
    Aggregate all 7 agent briefs into Major's morning brief.
    Grouped by goal_tag in priority order: CINCINNATI → ARR → USERS → OPS
    """
    # Collect all surfaced events across agents, tagged with agent_id
    all_events_by_goal: dict[str | None, list[str]] = {
        "cincinnati": [], "arr": [], "users": [], "ops": [], None: []
    }
    all_action_items: list[str] = []
    total_events  = 0
    total_pruned  = 0

    for agent_id, brief in agent_briefs.items():
        total_events += brief["total_events"]
        total_pruned += brief["pruned_events"]
        all_action_items.extend(brief["action_items"])

        # Re-fetch the agent's scored events to bucket by goal
        scored = _score_events(_events_last_24h(agent_id))
        for e in scored[:5]:  # top 5 per agent
            goal = e.get("goal_tag")
            bucket = goal if goal in all_events_by_goal else None
            label  = GOAL_LABELS.get(goal, "GENERAL")
            promoted = " [promoted]" if goal == "cincinnati" and e.get("importance", 0) < BRIEF_MIN_IMPORTANCE else ""
            line = f"  [{agent_id}] {e['event_type']}: {e['content']}{promoted}"
            all_events_by_goal[bucket].append(line)

    # Deduplicate action items
    seen: set[str] = set()
    deduped_actions = [a for a in all_action_items if not (a in seen or seen.add(a))]

    # Collect active goal tags
    active_goal_tags = [g for g in ("cincinnati", "arr", "users", "ops") if all_events_by_goal.get(g)]

    imessage_text = _format_imessage(
        date_str, all_events_by_goal, deduped_actions, total_events, total_pruned
    )

    return {
        "agent":  "major",
        "date":   date_str,
        "source": "sleep_cycle",
        "total_events_across_agents": total_events,
        "total_pruned":               total_pruned,
        "events_by_goal":             {k: v for k, v in all_events_by_goal.items() if v},
        "action_items":               deduped_actions,
        "goal_tags":                  active_goal_tags,
        "agent_summaries": {
            aid: {
                "events":     brief["total_events"],
                "surfaced":   brief["retained_events"],
                "actions":    len(brief["action_items"]),
            }
            for aid, brief in agent_briefs.items()
        },
        "imessage_text": imessage_text,
    }


def _format_imessage(
    date_str: str,
    events_by_goal: dict,
    action_items: list[str],
    total_events: int,
    total_pruned: int,
) -> str:
    lines = [
        f"Section 9 Morning Brief — {date_str}",
        f"({total_events} events, {total_pruned} pruned)",
        "",
    ]

    has_content = False

    # Cincinnati first — always
    for goal_tag in ("cincinnati", "arr", "users", "ops", None):
        bucket = events_by_goal.get(goal_tag, [])
        if not bucket:
            continue
        has_content = True
        label = GOAL_LABELS.get(goal_tag, "GENERAL")
        lines.append(f"▶ {label}")
        for line in bucket[:4]:
            lines.append(f"  •{line.strip()}")
        lines.append("")

    if action_items:
        lines.append("Action items:")
        for a in action_items:
            lines.append(f"  ▶ {a}")
        lines.append("")

    if not has_content and not action_items:
        lines.append("All quiet. No high-importance events in the last 24 hours.")
        lines.append("")

    lines.append("— Borma / Section 9")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_sleep_cycle() -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[sleep_cycle] Starting — {date_str}")

    # 1. Prune low-importance events globally (< 4 from DB)
    pruned = delete_below_importance(threshold=PRUNE_BELOW)
    print(f"[sleep_cycle] Pruned {pruned} low-importance events (importance < {PRUNE_BELOW})")

    # 2. Per-agent briefs (surface >= 7, Cincinnati >= 6)
    agent_briefs: dict[str, dict] = {}
    for agent_id in AGENTS:
        brief = _build_agent_brief(agent_id, date_str)
        agent_briefs[agent_id] = brief
        brief_path = QUEUE_DIR / f"{agent_id}_brief.json"
        brief_path.write_text(json.dumps(brief, indent=2))
        print(
            f"[sleep_cycle] [{agent_id}] → {brief_path.name} "
            f"({brief['retained_events']} surfaced / {brief['total_events']} total, "
            f"{len(brief['action_items'])} actions)"
        )

    # 3. Major's aggregated morning brief, grouped by goal
    morning = _build_morning_brief(agent_briefs, date_str)
    morning_path = QUEUE_DIR / "morning_brief.json"
    morning_path.write_text(json.dumps(morning, indent=2))
    print(f"[sleep_cycle] Morning brief → {morning_path.name}")
    print()
    print(morning["imessage_text"])
    print()
    print("[sleep_cycle] Done.")


def run_test_mode() -> None:
    """
    --test mode: read DB and print the morning brief preview without
    pruning the DB or writing any queue files.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[sleep_cycle --test] DRY RUN — {date_str}")
    print(f"[sleep_cycle --test] No DB pruning. No files written.\n")

    # Count what WOULD be pruned
    from section9.agent_memory import _get_conn as _gc
    conn = _gc()
    would_prune = conn.execute(
        "SELECT COUNT(*) FROM memory WHERE importance < ?", (PRUNE_BELOW,)
    ).fetchone()[0]
    conn.close()
    print(f"[sleep_cycle --test] Would prune: {would_prune} events (importance < {PRUNE_BELOW})")
    print()

    agent_briefs: dict[str, dict] = {}
    for agent_id in AGENTS:
        brief = _build_agent_brief(agent_id, date_str)
        agent_briefs[agent_id] = brief
        surfaced   = brief["retained_events"]
        total      = brief["total_events"]
        actions    = len(brief["action_items"])
        promoted   = sum(
            1 for h in brief["highlights"]
            if "[promoted]" in h
        )
        promo_str  = f", {promoted} cincinnati-promoted" if promoted else ""
        print(f"  [{agent_id:8s}] {surfaced:2d} surfaced / {total:2d} total{promo_str}  |  {actions} action(s)")

        for h in brief["highlights"]:
            print(f"             • {h}")

    morning = _build_morning_brief(agent_briefs, date_str)

    print()
    print("━" * 60)
    print("MORNING BRIEF PREVIEW (what Major receives)")
    print("━" * 60)
    print(morning["imessage_text"])
    print("━" * 60)
    print()
    print("[sleep_cycle --test] Done. Nothing written to disk.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Section 9 sleep cycle")
    p.add_argument("--test", action="store_true",
                   help="Dry run — preview brief without pruning DB or writing files")
    args = p.parse_args()

    if args.test:
        run_test_mode()
    else:
        run_sleep_cycle()
