#!/usr/bin/env python3
"""
Section 9 Obsidian Logger
Major calls this script to log entries to the vault.
Usage: python3 log_to_obsidian.py --agent major --content "Today's priorities..."
"""
import argparse
import datetime
import os
from pathlib import Path

VAULT = Path("/Users/aspenlaurent/Vedura Company/The Vedura Company")

AGENT_FOLDERS = {
    "major": "01 - Major/Daily Log.md",
    "batou": "02 - Batou/Task Log.md",
    "togusa": "03 - Togusa/Intel Log.md",
    "ishikawa": "04 - Ishikawa/Metrics Log.md",
    "saito": "05 - Saito/Copy Log.md",
    "paz": "06 - Paz/Outreach Log.md",
    "borma": "07 - Borma/Mycelium Log.md",
    "conversations": "11 - Conversations/Conversations Log.md",
    "metrics": "12 - Metrics/Tracker.md",
}

def log_entry(agent: str, content: str):
    filepath = VAULT / AGENT_FOLDERS[agent]
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {timestamp}\n{content}\n"
    
    with open(filepath, "a") as f:
        f.write(entry)
    
    print(f"Logged to {filepath}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True, choices=AGENT_FOLDERS.keys())
    parser.add_argument("--content", required=True)
    args = parser.parse_args()
    log_entry(args.agent, args.content)
