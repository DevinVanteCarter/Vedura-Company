# The Vedura Company

AI-powered platform for off-grid homesteaders.

© 2026 The Vedura Company. All rights reserved.
Unauthorized use, copying, or distribution prohibited.

---

## Products

### Zen Vision
AI platform for off-grid living — plant health scanning, solar management, and local AI advisor.
→ [zen-vision-sigma.vercel.app](https://zen-vision-sigma.vercel.app)

### BarnForge
Expert AI barndominium design assistant — floor plans, color systems, materials, 3D spatial walkthroughs, and off-grid integration.
→ `zen-vision-sigma.vercel.app/barnforge`

---

## Structure

```
/
├── index.html          ← Vedura Company website
├── app.html            ← Zen Vision demo
├── barnforge/
│   └── index.html      ← BarnForge app
├── api/
│   ├── advisor.js      ← Zen Vision AI advisor (Groq)
│   └── barnforge.js    ← BarnForge AI (Anthropic)
└── zenvision_api/      ← FastAPI backend (Railway)
```

## Env Vars (Vercel)
- `GROQ_API_KEY` — Zen Vision advisor
- `ANTHROPIC_API_KEY` — BarnForge
