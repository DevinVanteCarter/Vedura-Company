#!/usr/bin/env python3
"""
Section 9 — CLI event logger
Lets any agent (or human) log episodic events and update the knowledge graph
from the terminal or from OpenClaw flows.

USAGE — log an event:
    python3 section9/log_event.py \\
        --agent batou --type deploy \\
        --content "Railway fixed, API healthy" \\
        --entities "Railway,FastAPI" \\
        --importance 9 --goal cincinnati

USAGE — log an event AND add a knowledge graph node:
    python3 section9/log_event.py \\
        --agent togusa --type investor_found \\
        --content "Found Cintrifuse — Cincinnati pre-seed VC" \\
        --entities "Cintrifuse" --importance 8 --goal cincinnati \\
        --graph-node --entity-type investor --node-name "Cintrifuse" \\
        --node-properties '{"location": "Cincinnati", "focus": "startups"}'

USAGE — log an event AND add a knowledge graph edge:
    python3 section9/log_event.py \\
        --agent togusa --type relationship_found \\
        --content "Cintrifuse attending Cincinnati AI Week" \\
        --importance 7 --goal cincinnati \\
        --graph-edge --source "Cintrifuse" --target "Cincinnati" \\
        --relationship "attending" --weight 1.0

USAGE — just add a graph node (no event log):
    python3 section9/log_event.py \\
        --graph-node --entity-type investor --node-name "Cintrifuse" \\
        --node-properties '{"location": "Cincinnati"}'

USAGE — just add a graph edge (no event log):
    python3 section9/log_event.py \\
        --graph-edge --source "Cintrifuse" --target "Cincinnati" \\
        --relationship "attending"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from section9.agent_memory import log_event, AGENTS
    from section9.knowledge_graph import add_node, add_edge
except ModuleNotFoundError:
    from agent_memory import log_event, AGENTS      # type: ignore
    from knowledge_graph import add_node, add_edge  # type: ignore

GOAL_TAGS = ("cincinnati", "arr", "users", "ops")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Log a Section 9 episodic event and/or update the knowledge graph.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
agents:     {', '.join(AGENTS)}
goals:      {', '.join(GOAL_TAGS)}
importance: 0 (noise) → 10 (mission-critical) — don't log below 4
""",
    )

    # ── Event args ────────────────────────────────────────────────────
    event = p.add_argument_group("event logging (requires --agent, --type, --content)")
    event.add_argument("-a", "--agent",   help="Agent ID")
    event.add_argument("-t", "--type",    help="Event type label (e.g. deploy, research, outreach)")
    event.add_argument("-c", "--content", help="Full description of what happened")
    event.add_argument(
        "-e", "--entities", default="",
        help='Comma-separated entity names, e.g. "Railway,FastAPI"',
    )
    event.add_argument(
        "-i", "--importance", type=int, default=5, metavar="0-10",
        help="Importance score 0–10 (default: 5)",
    )
    event.add_argument(
        "-g", "--goal", choices=GOAL_TAGS, default=None, metavar="GOAL",
        help=f"Goal tag: {', '.join(GOAL_TAGS)}",
    )

    # ── Graph node args ───────────────────────────────────────────────
    gnode = p.add_argument_group("knowledge graph node (--graph-node to enable)")
    gnode.add_argument("--graph-node",      action="store_true", help="Add/update a knowledge graph node")
    gnode.add_argument("--entity-type",     help="Node entity type (agent, goal, investor, competitor, user, community, tech, project, person)")
    gnode.add_argument("--node-name",       help="Node name (unique identifier in the graph)")
    gnode.add_argument("--node-properties", default="{}", help='JSON string of node properties, e.g. \'{"firm": "XYZ"}\'')

    # ── Graph edge args ───────────────────────────────────────────────
    gedge = p.add_argument_group("knowledge graph edge (--graph-edge to enable)")
    gedge.add_argument("--graph-edge",   action="store_true", help="Add/update a knowledge graph edge")
    gedge.add_argument("--source",       help="Source node name")
    gedge.add_argument("--target",       help="Target node name")
    gedge.add_argument("--relationship", help="Edge relationship label (e.g. attending, invested_in, owns)")
    gedge.add_argument("--weight",       type=float, default=1.0, help="Edge weight 0.0–1.0 (default: 1.0)")

    # ── Output ────────────────────────────────────────────────────────
    p.add_argument("--json", action="store_true", help="Output result as JSON")

    return p.parse_args()


def validate_args(args: argparse.Namespace) -> list[str]:
    """Return list of validation error strings (empty = valid)."""
    errors = []

    has_event_args = bool(args.agent or args.type or args.content)
    wants_event = has_event_args

    if wants_event:
        if not args.agent:
            errors.append("--agent is required when logging an event")
        elif args.agent not in AGENTS:
            errors.append(f"Unknown agent '{args.agent}'. Must be one of: {', '.join(AGENTS)}")
        if not args.type:
            errors.append("--type is required when logging an event")
        if not args.content:
            errors.append("--content is required when logging an event")
        if not 0 <= args.importance <= 10:
            errors.append("--importance must be 0–10")

    if args.graph_node:
        if not args.entity_type:
            errors.append("--entity-type is required with --graph-node")
        if not args.node_name:
            errors.append("--node-name is required with --graph-node")
        try:
            json.loads(args.node_properties)
        except json.JSONDecodeError as exc:
            errors.append(f"--node-properties is not valid JSON: {exc}")

    if args.graph_edge:
        if not args.source:
            errors.append("--source is required with --graph-edge")
        if not args.target:
            errors.append("--target is required with --graph-edge")
        if not args.relationship:
            errors.append("--relationship is required with --graph-edge")

    if not wants_event and not args.graph_node and not args.graph_edge:
        errors.append("Nothing to do. Provide event args (--agent/--type/--content) and/or --graph-node/--graph-edge.")

    return errors


def main() -> None:
    args = parse_args()

    errors = validate_args(args)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    result: dict = {}
    has_event = bool(args.agent and args.type and args.content)

    # ── Log event ─────────────────────────────────────────────────────
    if has_event:
        entities = [e.strip() for e in args.entities.split(",") if e.strip()] if args.entities else []
        event_id = log_event(
            agent_id=args.agent,
            event_type=args.type,
            content=args.content,
            entities=entities,
            importance=args.importance,
            goal_tag=args.goal,
        )
        result["event"] = {
            "ok": True,
            "event_id": event_id,
            "agent_id": args.agent,
            "event_type": args.type,
            "importance": args.importance,
            "goal_tag": args.goal,
        }

    # ── Add graph node ────────────────────────────────────────────────
    if args.graph_node:
        props = json.loads(args.node_properties)
        node_id = add_node(
            entity_type=args.entity_type,
            name=args.node_name,
            properties=props,
        )
        result["node"] = {
            "ok": True,
            "node_id": node_id,
            "entity_type": args.entity_type,
            "name": args.node_name,
        }

    # ── Add graph edge ────────────────────────────────────────────────
    if args.graph_edge:
        try:
            edge_id = add_edge(
                source_name=args.source,
                target_name=args.target,
                relationship=args.relationship,
                weight=args.weight,
            )
            result["edge"] = {
                "ok": True,
                "edge_id": edge_id,
                "source": args.source,
                "target": args.target,
                "relationship": args.relationship,
            }
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)

    # ── Output ────────────────────────────────────────────────────────
    if args.json:
        print(json.dumps(result))
        return

    if "event" in result:
        e = result["event"]
        goal_str = f" [{e['goal_tag']}]" if e.get("goal_tag") else ""
        imp = e["importance"]
        imp_bar = "█" * imp + "░" * (10 - imp)
        print(f"[{e['agent_id']}] event #{e['event_id']} logged{goal_str}")
        print(f"  type:       {e['event_type']}")
        print(f"  content:    {args.content}")
        if args.entities:
            ents = [x.strip() for x in args.entities.split(",") if x.strip()]
            if ents:
                print(f"  entities:   {', '.join(ents)}")
        print(f"  importance: {imp_bar} {imp}/10")

    if "node" in result:
        n = result["node"]
        print(f"  graph node: [{n['entity_type']}] \"{n['name']}\" → id={n['node_id']}")

    if "edge" in result:
        ed = result["edge"]
        print(f"  graph edge: \"{ed['source']}\" --[{ed['relationship']}]-→ \"{ed['target']}\" → id={ed['edge_id']}")


if __name__ == "__main__":
    main()
