from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .agents.aria import aria
from .agents.base_agent import BaseAgent, PerformanceSnapshot
from .apip.lifecycle import APIPLifecycle
from .apip.schema import APIP, FailureMode, InterventionPlan, InterventionStep, InterventionTier
from .demo.full_scenario import FullDemoScenario
from .mesh.mesh import AgentMesh, MeshDisruptionScenario, mesh
from .simulation.degradation import DegradationEngine, DegradationMode
from .simulation.scenarios import ALL_SCENARIOS

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_agents: dict[str, BaseAgent] = {aria.agent_id: aria}
_engines: dict[str, DegradationEngine] = {aria.agent_id: DegradationEngine(aria)}
_active_apips: dict[str, APIP] = {}
_sim_running: bool = False
_ws_clients: list[WebSocket] = []

mesh.add_agent(aria, connect_to_all=False)


# ---------------------------------------------------------------------------
# Background simulation loop
# ---------------------------------------------------------------------------

async def _simulation_loop() -> None:
    global _sim_running
    while _sim_running:
        await asyncio.sleep(3)
        for agent_id, engine in _engines.items():
            agent = _agents[agent_id]
            snapshot = engine.tick()
            apip = APIPLifecycle.check_trigger(agent)
            if apip and apip.apip_id not in _active_apips:
                _active_apips[apip.apip_id] = apip

        metrics_payload = _build_metrics_payload()
        for ws in list(_ws_clients):
            try:
                await ws.send_json(metrics_payload)
            except Exception:
                _ws_clients.remove(ws)


def _build_metrics_payload() -> dict:
    payload: dict[str, Any] = {"timestamp": datetime.utcnow().isoformat(), "agents": []}
    mesh_by_id = {a["agent_id"]: a for a in mesh.status()["agents"]}
    for agent in _agents.values():
        snap = agent.latest_snapshot()
        mesh_info = mesh_by_id.get(agent.agent_id, {})
        payload["agents"].append({
            "agent_id": agent.agent_id,
            "agent_name": agent.agent_name,
            "role": agent.role,
            "health": agent.get_health_status(),
            "metrics": snap.to_metrics() if snap else {},
            "context_weight": mesh_info.get("context_weight", 0.0),
            "baseline_weight": mesh_info.get("baseline_weight", 0.0),
            "crowding_effect": mesh_info.get("crowding_effect", 1.0),
            "active_apip": next(
                (a.apip_id for a in _active_apips.values() if a.agent_id == agent.agent_id),
                None,
            ),
        })
    return payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="APIP Simulation API", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@app.get("/agents")
def list_agents():
    return [
        {
            "agent_id": a.agent_id,
            "agent_name": a.agent_name,
            "role": a.role,
            "health": a.get_health_status(),
        }
        for a in _agents.values()
    ]


@app.get("/agents/{agent_id}/metrics")
def get_agent_metrics(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return [
        {**s.to_metrics(), "timestamp": s.timestamp.isoformat(), "notes": s.notes}
        for s in agent._snapshots
    ]


@app.get("/agents/{agent_id}/contract")
def get_agent_contract(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    c = agent.contract
    return {
        "task_surface": c.task_surface,
        "metrics": c.metrics,
        "thresholds": c.thresholds,
        "drift_sensitivity": c.drift_sensitivity,
        "owner": c.owner,
        "created_at": c.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Simulation control
# ---------------------------------------------------------------------------

class TickRequest(BaseModel):
    ticks: int = 1
    scenario: str | None = None


class InjectRequest(BaseModel):
    agent_id: str
    mode: str
    intensity: float = 0.5


@app.post("/simulation/tick")
async def simulation_tick(body: TickRequest):
    global _sim_running
    scenario = ALL_SCENARIOS.get(body.scenario) if body.scenario else None
    results = []

    for _ in range(body.ticks):
        for agent_id, engine in _engines.items():
            agent = _agents[agent_id]
            if scenario:
                scenario.apply_at_tick(engine, engine.current_tick + 1)
            snapshot = engine.tick()
            apip = APIPLifecycle.check_trigger(agent)
            if apip and apip.apip_id not in _active_apips:
                _active_apips[apip.apip_id] = apip
            results.append({
                "agent_id": agent_id,
                "tick": engine.current_tick,
                "metrics": snapshot.to_metrics(),
                "health": agent.get_health_status(),
                "apip_triggered": apip.apip_id if apip else None,
            })

    metrics_payload = _build_metrics_payload()
    for ws in list(_ws_clients):
        try:
            await ws.send_json(metrics_payload)
        except Exception:
            _ws_clients.remove(ws)

    return results


@app.post("/simulation/reset")
def simulation_reset():
    global _sim_running
    _sim_running = False
    for engine in _engines.values():
        engine.reset()
    _active_apips.clear()
    return {"status": "reset"}


@app.post("/simulation/inject")
def simulation_inject(body: InjectRequest):
    engine = _engines.get(body.agent_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        mode = DegradationMode(body.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {body.mode}")
    engine.inject(mode, body.intensity)
    return {"status": "injected", "mode": mode, "intensity": body.intensity}


# ---------------------------------------------------------------------------
# APIP records
# ---------------------------------------------------------------------------

@app.get("/apips")
def list_apips():
    records = APIPLifecycle.load_all()
    return [
        {
            "apip_id": r["apip_id"],
            "agent_id": r["agent_id"],
            "phase": r["phase"],
            "created_at": r["created_at"],
            "exit_outcome": r.get("exit_outcome"),
        }
        for r in records
    ]


@app.get("/apips/{apip_id}")
def get_apip(apip_id: str):
    record = APIPLifecycle.load(apip_id)
    if not record:
        raise HTTPException(status_code=404, detail="APIP not found")
    return record


class InterventionRequest(BaseModel):
    tier: int
    description: str


@app.post("/apips/{apip_id}/intervene")
def apply_intervention(apip_id: str, body: InterventionRequest):
    record = APIPLifecycle.load(apip_id)
    if not record:
        raise HTTPException(status_code=404, detail="APIP not found")
    apip = _active_apips.get(apip_id)
    if not apip:
        raise HTTPException(status_code=400, detail="APIP not active in current session")
    try:
        tier = InterventionTier(body.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="tier must be 1, 2, or 3")
    apip.intervention_plan = InterventionPlan(
        tier=tier,
        steps=[InterventionStep(
            description=body.description,
            estimated_effort="medium",
            expected_impact="medium",
        )],
    )
    APIPLifecycle.open_window(apip, duration_ticks=10)
    return {"status": "intervention_applied", "apip_id": apip_id}


class CheckinRequest(BaseModel):
    agent_id: str


@app.post("/apips/{apip_id}/checkin")
def record_checkin(apip_id: str, body: CheckinRequest):
    apip = _active_apips.get(apip_id)
    if not apip:
        raise HTTPException(status_code=404, detail="Active APIP not found")
    agent = _agents.get(body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    snapshot = agent.latest_snapshot()
    if not snapshot:
        raise HTTPException(status_code=400, detail="No snapshot available")
    checkin = APIPLifecycle.record_checkin(apip, snapshot)
    return {
        "tick": checkin.tick,
        "trajectory": checkin.trajectory,
        "escalated": checkin.escalated,
    }


@app.post("/apips/{apip_id}/evaluate-exit")
def evaluate_exit(apip_id: str, body: CheckinRequest):
    apip = _active_apips.get(apip_id)
    if not apip:
        raise HTTPException(status_code=404, detail="Active APIP not found")
    agent = _agents.get(body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    outcome = APIPLifecycle.evaluate_exit(apip, agent)
    if outcome == "RESOLVED":
        _active_apips.pop(apip_id, None)
    return {"exit_outcome": outcome, "apip_id": apip_id}


# ---------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------

class AddAgentRequest(BaseModel):
    agent_id: str
    agent_name: str
    role: str
    initial_weight: float | None = None


@app.get("/mesh/status")
def mesh_status():
    return mesh.status()


@app.post("/mesh/add-agent")
def mesh_add_agent(body: AddAgentRequest):
    from .agents.base_agent import BehavioralContract

    existing = _agents.get(body.agent_id)
    if existing:
        mesh.add_agent(existing, initial_weight=body.initial_weight)
        return {"status": "added_existing", "agent_id": body.agent_id, "mesh": mesh.status()}

    new_agent = BaseAgent(
        agent_id=body.agent_id,
        agent_name=body.agent_name,
        role=body.role,
        contract=aria.contract,
    )
    _agents[new_agent.agent_id] = new_agent
    _engines[new_agent.agent_id] = DegradationEngine(new_agent)
    mesh.add_agent(new_agent, initial_weight=body.initial_weight)
    return {"status": "added", "agent_id": new_agent.agent_id, "mesh": mesh.status()}


@app.post("/mesh/disruption-scenario")
def run_disruption_scenario():
    """
    Runs the Section 7.3 mesh disruption scenario in an isolated context and
    registers scenario agents into the live simulation so they appear on the
    mesh view and WebSocket stream.
    """
    scenario_mesh, report = MeshDisruptionScenario.run()

    # Register scenario agents in global state so they show up in /agents and WS
    for agent_id, agent in scenario_mesh.agents.items():
        if agent_id not in _agents:
            _agents[agent_id] = agent
            _engines[agent_id] = DegradationEngine(agent)
        if agent_id not in mesh.agents:
            w = scenario_mesh.context_weights.get(agent_id)
            mesh.add_agent(agent, initial_weight=w)
            mesh.baseline_weights[agent_id] = scenario_mesh.baseline_weights.get(
                agent_id, w or 0.0
            )

    return report


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

@app.post("/demo/run-full-scenario")
def run_full_scenario():
    """
    Executes the scripted 37-tick walkthrough covering all paper sections:
      - Section 4: APIP trigger and attribution (BEHAVIORAL_DRIFT on Aria)
      - Section 5: Intervention, check-in, and exit lifecycle
      - Section 6: Drift-only trigger (ALIGNMENT_CREEP)
      - Section 7.3: Causal attribution failure via mesh context crowding
      - Section 7.4: MeshAudit and context scoping recovery

    Runs in an isolated context; registers scenario agents into the live
    simulation at completion so they appear on the mesh view.
    """
    result = FullDemoScenario.run()

    # Register agents that appeared in the demo into the live simulation so
    # they show up on the mesh view and WebSocket stream.
    for mesh_agent in result["final_mesh"]["agents"]:
        aid = mesh_agent["agent_id"]
        if aid not in _agents:
            stub = BaseAgent(
                agent_id=aid,
                agent_name=mesh_agent.get("agent_name", aid),
                role="demo",
                contract=aria.contract,
            )
            _agents[aid] = stub
            _engines[aid] = DegradationEngine(stub)
        if aid not in mesh.agents:
            mesh.add_agent(
                _agents[aid],
                initial_weight=mesh_agent.get("context_weight"),
            )

    return result


# ---------------------------------------------------------------------------
# WebSocket — live metric streaming
# ---------------------------------------------------------------------------

@app.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        await websocket.send_json(_build_metrics_payload())
        while True:
            await websocket.receive_text()  # keep alive; client can send pings
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
