Vedura — Full-Stack AI Platform
A production AI platform built solo by Devin Carter — combining computer vision, LLM agents, and carbon-aware compute scheduling. FastAPI backend, Vercel frontend, deployed live.
What it does
Zen Vision — AI for off-grid living

Computer-vision plant health analysis (OpenCV — HSV color analysis, edge detection, morphological ops)
Solar load-routing engine with priority-based, explainable decisions
Local-first AI advisor (runs against your own hardware for privacy)

Green Scheduler — carbon- and cost-aware AI job routing

Schedules AI workloads into low-carbon, low-cost grid windows
Uses an LLM as a live reasoning engine to balance urgency against grid conditions
Built around a simple thesis: as AI gets expensive to run, when you run it matters

BarnForge — AI barndominium design assistant

Floor plans, materials, and off-grid integration guidance

Stack

Backend: Python, FastAPI (deployed on Railway)
Frontend: HTML/CSS/JS, deployed on Vercel
AI: LLM API integration; local inference via Ollama; computer vision via OpenCV
Vision: OpenCV, NumPy, scikit-image

Architecture
/
├── index.html          Company website
├── app.html            Zen Vision demo
├── barnforge/          BarnForge app
├── api/                Serverless AI functions (Vercel)
└── zenvision_api/      FastAPI backend (Railway)
About
Built end-to-end by Devin Carter — data operations professional and AI systems builder, Loveland, Ohio. This project demonstrates full-stack AI development: production deployment, LLM integration, computer vision, and a focus on the operating economics of AI.
