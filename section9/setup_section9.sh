#!/bin/bash
# ============================================================
# SECTION 9 OPENCLAW SETUP SCRIPT
# The Vedura Company
# Run this in your terminal on your Mac Studio
# ============================================================

set -e  # exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$HOME/.openclaw/workspaces"

echo ""
echo "🌱 VEDURA / SECTION 9 — OpenClaw Multi-Agent Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── STEP 1: Add all agents ──────────────────────────────────
echo "▶ Step 1: Registering agents..."
openclaw agents add major batou togusa ishikawa saito paz borma
echo "✅ All 7 agents registered"
echo ""

# ── STEP 2: Write openclaw.json config ─────────────────────
echo "▶ Step 2: Writing ~/.openclaw/openclaw.json..."
mkdir -p "$HOME/.openclaw"
cp "$SCRIPT_DIR/openclaw.json" "$HOME/.openclaw/openclaw.json"
echo "✅ Config written"
echo ""

# ── STEP 3: Create workspace directories ───────────────────
echo "▶ Step 3: Creating agent workspaces..."
for agent in major batou togusa ishikawa saito paz borma; do
    mkdir -p "$WORKSPACE_ROOT/$agent"
    echo "  📁 Created workspace: $WORKSPACE_ROOT/$agent"
done
echo ""

# ── STEP 4: Write SOUL files ────────────────────────────────
echo "▶ Step 4: Writing SOUL files..."

for agent in major batou togusa ishikawa saito paz borma; do
    SRC="$SCRIPT_DIR/SOUL_${agent}.md"
    DST="$WORKSPACE_ROOT/$agent/SOUL.md"
    if [ -f "$SRC" ]; then
        cp "$SRC" "$DST"
        echo "  🧠 SOUL written: $agent"
    else
        echo "  ⚠️  Missing source: $SRC — skipping $agent"
    fi
done
echo ""

# ── STEP 5: Restart gateway ─────────────────────────────────
echo "▶ Step 5: Restarting OpenClaw gateway..."
openclaw gateway restart
echo "✅ Gateway restarted"
echo ""

# ── DONE ─────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SECTION 9 IS ONLINE"
echo ""
echo "Agents: major · batou · togusa · ishikawa · saito · paz · borma"
echo "Dashboard: http://127.0.0.1:18789"
echo ""
echo "Workspaces:"
for agent in major batou togusa ishikawa saito paz borma; do
    echo "  ~/.openclaw/workspaces/$agent/SOUL.md"
done
echo ""
echo "Config: ~/.openclaw/openclaw.json"
echo ""
echo "Cincinnati: June 9, 2026. Let's go. 🌱☀️"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
