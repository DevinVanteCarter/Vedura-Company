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
from fastapi.responses import HTMLResponse
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


_BRAIN_GRAPH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SECTION 9 · VEDURA BRAIN GRAPH</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#050505;color:#F0EDD8;font-family:'DM Mono',monospace;overflow:hidden;width:100vw;height:100vh}
  #header{position:fixed;top:0;left:0;right:0;z-index:100;padding:18px 32px;
    display:flex;align-items:center;justify-content:space-between;
    background:rgba(5,5,5,0.85);backdrop-filter:blur(12px);
    border-bottom:1px solid rgba(240,237,216,0.08)}
  #title{font-family:'Cormorant Garamond',serif;font-size:1.15rem;font-weight:300;
    letter-spacing:.3em;color:#F0EDD8}
  #title span{color:#FFD166}
  #counters{display:flex;gap:28px;font-size:.6rem;letter-spacing:.15em;color:rgba(240,237,216,0.45)}
  #counters .val{color:#F0EDD8;font-size:.72rem}
  #graph{width:100%;height:100%;cursor:grab}
  #graph:active{cursor:grabbing}
  svg{width:100%;height:100%}
  .node circle{cursor:pointer;stroke-width:1.5px;transition:r .2s}
  .node text{font-family:'Cormorant Garamond',serif;font-size:11px;font-weight:400;
    fill:#F0EDD8;pointer-events:none;text-shadow:0 1px 3px #050505}
  .link{stroke:rgba(240,237,216,0.12);stroke-width:1px}
  .link:hover{stroke:rgba(240,237,216,0.6);stroke-width:2px}
  #edge-tooltip{position:fixed;background:rgba(5,5,5,0.92);border:1px solid rgba(255,209,102,0.3);
    padding:6px 12px;font-size:.6rem;letter-spacing:.12em;color:#FFD166;pointer-events:none;
    display:none;z-index:200}
  #panel{position:fixed;right:0;top:0;bottom:0;width:320px;background:rgba(5,5,5,0.95);
    border-left:1px solid rgba(240,237,216,0.08);padding:72px 24px 24px;
    transform:translateX(320px);transition:transform .3s ease;overflow-y:auto;z-index:50}
  #panel.open{transform:translateX(0)}
  #panel-close{position:absolute;top:18px;right:18px;background:none;border:none;
    color:rgba(240,237,216,0.4);font-size:1rem;cursor:pointer;font-family:'DM Mono',monospace}
  #panel-close:hover{color:#F0EDD8}
  #panel h2{font-family:'Cormorant Garamond',serif;font-size:1.3rem;font-weight:400;
    margin-bottom:6px;word-break:break-word}
  #panel .type-badge{font-size:.55rem;letter-spacing:.2em;padding:3px 8px;
    border:1px solid;margin-bottom:18px;display:inline-block}
  #panel .props{font-size:.65rem;line-height:1.8;color:rgba(240,237,216,0.7)}
  #panel .props .key{color:#FFD166;letter-spacing:.08em}
  .ring{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
    width:200px;height:200px;pointer-events:none;z-index:10;display:none}
  .ring circle{fill:none;stroke:rgba(255,209,102,0.04);stroke-width:1}
</style>
</head>
<body>
<div id="header">
  <div id="title"><span>SECTION 9</span> · VEDURA BRAIN GRAPH</div>
  <div id="counters">
    <div>NODES <span class="val" id="c-nodes">—</span></div>
    <div>EDGES <span class="val" id="c-edges">—</span></div>
    <div>AGENTS <span class="val" id="c-agents">—</span></div>
  </div>
</div>
<div id="graph"></div>
<div id="edge-tooltip"></div>
<div id="panel">
  <button id="panel-close">✕</button>
  <div id="panel-content"></div>
</div>
<script>
const TYPE_COLOR = {
  agent:'#FFD166', goal:'#52B788', project:'#95D5B2', tech:'#888780',
  competitor:'#E24B4A', person:'#F0EDD8', investor:'#A3783A',
  community:'#52B788', framework:'#FFD166', metric:'#95D5B2'
};
const DEFAULT_COLOR = '#888780';

function nodeColor(type){ return TYPE_COLOR[type] || DEFAULT_COLOR; }
function nodeR(connections){ return Math.max(6, Math.min(24, 6 + connections * 1.8)); }

const panel = document.getElementById('panel');
const edgeTip = document.getElementById('edge-tooltip');

document.getElementById('panel-close').onclick = () => panel.classList.remove('open');

async function init(){
  const data = await fetch('/brain').then(r=>r.json());
  const nodes = data.nodes.map(n=>({...n}));
  const edgeRaw = data.edges;

  // Count connections per node id
  const connCount = {};
  nodes.forEach(n=>{ connCount[n.id]=0; });
  edgeRaw.forEach(e=>{ connCount[e.source]=(connCount[e.source]||0)+1; connCount[e.target]=(connCount[e.target]||0)+1; });

  // Build lookup by name for edges
  const idByName = {}; nodes.forEach(n=>{ idByName[n.name]=n.id; });
  const links = edgeRaw.map(e=>({
    source: e.source, target: e.target,
    relationship: e.relationship, weight: e.weight,
    _sid: e.source, _tid: e.target
  }));

  // Update counters
  document.getElementById('c-nodes').textContent = nodes.length;
  document.getElementById('c-edges').textContent = links.length;
  document.getElementById('c-agents').textContent = nodes.filter(n=>n.entity_type==='agent').length;

  const W = window.innerWidth, H = window.innerHeight;
  const svg = d3.select('#graph').append('svg')
    .attr('width', W).attr('height', H)
    .call(d3.zoom().scaleExtent([0.2,4]).on('zoom', e=>{g.attr('transform',e.transform)}));

  const g = svg.append('g');

  // Grid-like decorative lines
  const defs = svg.append('defs');
  const grd = defs.append('radialGradient').attr('id','bgGrad').attr('cx','50%').attr('cy','50%').attr('r','50%');
  grd.append('stop').attr('offset','0%').attr('stop-color','rgba(255,209,102,0.03)');
  grd.append('stop').attr('offset','100%').attr('stop-color','rgba(5,5,5,0)');

  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d=>d.name).distance(d=>120/d.weight).strength(0.6))
    .force('charge', d3.forceManyBody().strength(-280))
    .force('center', d3.forceCenter(W/2, H/2))
    .force('collision', d3.forceCollide(d=>nodeR(connCount[d.id]||0)+8));

  const link = g.append('g').selectAll('line').data(links).join('line')
    .attr('class','link')
    .on('mouseover', (event,d)=>{
      edgeTip.style.display='block';
      edgeTip.style.left=(event.clientX+12)+'px';
      edgeTip.style.top=(event.clientY-10)+'px';
      edgeTip.textContent=d.relationship.toUpperCase().replace(/_/g,' ');
    })
    .on('mousemove', event=>{
      edgeTip.style.left=(event.clientX+12)+'px';
      edgeTip.style.top=(event.clientY-10)+'px';
    })
    .on('mouseout', ()=>{ edgeTip.style.display='none'; });

  const node = g.append('g').selectAll('g').data(nodes).join('g')
    .attr('class','node')
    .call(d3.drag()
      .on('start',(e,d)=>{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
      .on('drag',(e,d)=>{ d.fx=e.x; d.fy=e.y; })
      .on('end',(e,d)=>{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }));

  node.append('circle')
    .attr('r', d=>nodeR(connCount[d.id]||0))
    .attr('fill', d=>nodeColor(d.entity_type)+'22')
    .attr('stroke', d=>nodeColor(d.entity_type))
    .on('mouseover', function(){ d3.select(this).attr('r', d=>nodeR(connCount[d.id]||0)+3); })
    .on('mouseout', function(){ d3.select(this).attr('r', d=>nodeR(connCount[d.id]||0)); })
    .on('click', (event,d)=>{ event.stopPropagation(); showPanel(d); });

  node.append('text')
    .attr('dy', d=>nodeR(connCount[d.id]||0)+13)
    .attr('text-anchor','middle')
    .text(d=>d.name);

  sim.on('tick', ()=>{
    link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
        .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    node.attr('transform',d=>`translate(${d.x},${d.y})`);
  });

  svg.on('click', ()=>panel.classList.remove('open'));
}

function showPanel(d){
  const color = nodeColor(d.entity_type);
  let propsHtml = '';
  if(d.properties && Object.keys(d.properties).length){
    propsHtml = Object.entries(d.properties).map(([k,v])=>{
      const val = typeof v === 'object' ? JSON.stringify(v) : v;
      return `<div><span class="key">${k}</span>: ${val}</div>`;
    }).join('');
  } else {
    propsHtml = '<div style="opacity:.4">no properties</div>';
  }
  document.getElementById('panel-content').innerHTML = `
    <h2>${d.name}</h2>
    <div class="type-badge" style="color:${color};border-color:${color}40">${d.entity_type.toUpperCase()}</div>
    <div class="props">${propsHtml}</div>
  `;
  panel.classList.add('open');
}

init();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def brain_graph_ui():
    """Serve the interactive force-directed brain graph visualization."""
    return HTMLResponse(content=_BRAIN_GRAPH_HTML)


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
