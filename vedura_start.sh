#!/bin/bash
# ============================================
# VEDURA COMPANY — STARTUP SCRIPT
# Launches all Zen Vision services at once
# Run with: bash ~/vedura_start.sh
# ============================================

GREEN='\033[0;32m'
MOSS='\033[0;36m'
CREAM='\033[0;33m'
RESET='\033[0m'

echo ""
echo -e "${GREEN}================================================${RESET}"
echo -e "${GREEN}  🌱 THE VEDURA COMPANY 🌞${RESET}"
echo -e "${GREEN}  Zen Vision Startup Sequence${RESET}"
echo -e "${GREEN}================================================${RESET}"
echo ""

# Get local IP
IP=$(ipconfig getifaddr en1 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || echo "unknown")

# ─────────────────────────────────────────────
# STEP 0 — Start Nexus AI gateway
# ─────────────────────────────────────────────
~/.nexus/bin/nexus --config '/Users/aspenlaurent/Vedura Company/nexus.toml' &
echo -e "${GREEN}  ✅ Nexus gateway started on http://localhost:6000${RESET}"
sleep 1

# ─────────────────────────────────────────────
# STEP 1 — Kill anything already running
# ─────────────────────────────────────────────
echo -e "${CREAM}Cleaning up previous sessions...${RESET}"
pkill -f uvicorn 2>/dev/null
pkill -f "http.server" 2>/dev/null
pkill -9 ollama 2>/dev/null
sleep 2

# ─────────────────────────────────────────────
# STEP 2 — Start Ollama
# ─────────────────────────────────────────────
echo -e "${CREAM}Starting Ollama (local AI)...${RESET}"
OLLAMA_ORIGINS="*" OLLAMA_HOST="0.0.0.0" ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!
sleep 3

if kill -0 $OLLAMA_PID 2>/dev/null; then
  echo -e "${GREEN}  ✅ Ollama running (PID $OLLAMA_PID)${RESET}"
else
  echo -e "  ⚠️  Ollama may already be running via the menu bar app"
fi

# ─────────────────────────────────────────────
# STEP 3 — Start Zen Vision API
# ─────────────────────────────────────────────
echo -e "${CREAM}Starting Zen Vision API...${RESET}"
cd '/Users/aspenlaurent/Vedura Company/zenvision_api'
uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/zenvision_api.log 2>&1 &
API_PID=$!
sleep 3

if kill -0 $API_PID 2>/dev/null; then
  echo -e "${GREEN}  ✅ Zen Vision API running (PID $API_PID)${RESET}"
else
  echo -e "  ❌ API failed to start — check /tmp/zenvision_api.log"
fi

# ─────────────────────────────────────────────
# STEP 4 — Start PWA web server
# ─────────────────────────────────────────────
echo -e "${CREAM}Starting PWA web server...${RESET}"
cd ~/Downloads/zenvision_pwa
python3 -m http.server 3001 > /tmp/zenvision_pwa.log 2>&1 &
PWA_PID=$!
sleep 1

if kill -0 $PWA_PID 2>/dev/null; then
  echo -e "${GREEN}  ✅ PWA server running (PID $PWA_PID)${RESET}"
else
  echo -e "  ❌ PWA server failed — check /tmp/zenvision_pwa.log"
fi

# ─────────────────────────────────────────────
# STEP 5 — Start OpenClaw
# ─────────────────────────────────────────────
echo -e "${CREAM}Starting OpenClaw agent...${RESET}"
openclaw gateway start > /tmp/openclaw.log 2>&1 &
sleep 2
echo -e "${GREEN}  ✅ OpenClaw agent started${RESET}"

# ─────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}================================================${RESET}"
echo -e "${GREEN}  🌱 VEDURA IS ALIVE 🌞${RESET}"
echo -e "${GREEN}================================================${RESET}"
echo ""
echo -e "${MOSS}  Mac browser:${RESET}  http://localhost:3001/zenvision_demo.html"
echo -e "${MOSS}  iPhone:${RESET}       http://$IP:3001/zenvision_demo.html"
echo -e "${MOSS}  API docs:${RESET}     http://localhost:8000/docs"
echo -e "${MOSS}  OpenClaw:${RESET}     http://127.0.0.1:18789"
echo -e "${MOSS}  Nexus:${RESET}        http://localhost:6000"
echo ""
echo -e "${CREAM}  Your IP address: $IP${RESET}"
echo -e "${CREAM}  To stop everything: bash ~/vedura_stop.sh${RESET}"
echo ""
echo -e "${GREEN}  May your plants thrive and your energy be sustainable.${RESET}"
echo ""
