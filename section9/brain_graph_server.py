"""
Section 9 — Brain Graph Server
Lightweight FastAPI service exposing the knowledge graph and episodic
memory store to the browser and to agent CLI tools.

Run:
    uvicorn section9.brain_graph_server:app --port 8765 --reload

Endpoints:
    GET  /health         → liveness probe
    GET  /brain          → full knowledge graph (nodes + edges)
    POST /memory/log     → write an episodic event
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from section9.knowledge_graph import export_json
    from section9.agent_memory import log_event, AGENTS
except ModuleNotFoundError:
    from knowledge_graph import export_json  # type: ignore
    from agent_memory import log_event, AGENTS  # type: ignore

app = FastAPI(
    title="Section 9 Brain Graph",
    description="Knowledge graph + episodic memory API for the 7 OpenClaw agents",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GoalTag = Literal["cincinnati", "arr", "users", "ops"]


class LogEventRequest(BaseModel):
    agent_id:   str                 = Field(..., description=f"One of: {AGENTS}")
    event_type: str                 = Field(..., description="Short label, e.g. 'deploy'")
    content:    str                 = Field(..., description="Full description of the event")
    entities:   Optional[list[str]] = Field(default=None)
    importance: int                 = Field(default=5, ge=0, le=10)
    goal_tag:   Optional[GoalTag]   = Field(default=None)


class LogEventResponse(BaseModel):
    ok:       bool
    event_id: int
    agent_id: str


@app.get("/health")
def health():
    return {"status": "alive", "service": "section9-brain-graph"}


@app.get("/brain")
def get_brain():
    """Return the full knowledge graph as { nodes: [...], edges: [...] }."""
    try:
        return export_json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/memory/log", response_model=LogEventResponse)
def memory_log(req: LogEventRequest):
    """Write an episodic event to the agent memory store."""
    if req.agent_id not in AGENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent '{req.agent_id}'. Must be one of: {AGENTS}",
        )
    try:
        event_id = log_event(
            agent_id=req.agent_id,
            event_type=req.event_type,
            content=req.content,
            entities=req.entities,
            importance=req.importance,
            goal_tag=req.goal_tag,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return LogEventResponse(ok=True, event_id=event_id, agent_id=req.agent_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("section9.brain_graph_server:app", host="0.0.0.0", port=8765, reload=True)
