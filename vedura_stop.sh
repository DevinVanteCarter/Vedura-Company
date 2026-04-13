#!/bin/bash
# ============================================
# VEDURA COMPANY — STOP SCRIPT
# Shuts down all Zen Vision services
# Run with: bash ~/vedura_stop.sh
# ============================================

echo ""
echo "🛑 Shutting down Vedura services..."

pkill -f "nexus --config" 2>/dev/null && echo "  ✅ Nexus stopped"
pkill -f uvicorn 2>/dev/null && echo "  ✅ Zen Vision API stopped"
pkill -f "http.server 3001" 2>/dev/null && echo "  ✅ PWA server stopped"
pkill -9 ollama 2>/dev/null && echo "  ✅ Ollama stopped"
openclaw gateway stop 2>/dev/null && echo "  ✅ OpenClaw stopped"

echo ""
echo "  All Vedura services stopped. 🌱"
echo ""
