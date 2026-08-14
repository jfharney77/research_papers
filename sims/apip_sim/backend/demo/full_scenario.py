"""
Full scripted walkthrough of the APIP lifecycle across two degradation arcs
and a mesh disruption event, as described in the paper.

Tick layout (approximate — actual trigger ticks depend on drift detection):
  1-5   : All agents healthy, no APIPs
  6-12  : BEHAVIORAL_DRIFT injected into Aria (stale RAG simulation)
  ~13   : APIP triggers on Aria → BEHAVIORAL_DRIFT attribution → Tier 2 plan
  14-16 : Drift resolved; metrics recovering
  17    : Check-in 1 → "improving"
  18-19 : Stable
  20    : Exit evaluation → RESOLVED
  21    : Stable
  22-27 : ALIGNMENT_CREEP injected into Aria (slow drift, no absolute breach)
  ~26   : Drift trigger fires on Aria
  28-29 : Stable pre-mesh
  30    : AgentN added to mesh (initial_weight=0.40); peers compressed to ~0.20
  31-35 : BillingAgent and EscalationAgent degrade from context crowding;
          APIPs fire; attribution → UNKNOWN_EXOGENOUS
  36    : MeshAudit: identifies context-weight compression correlated with AgentN
  37    : Context scoping applied; peer agents recover
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..agents.base_agent import BaseAgent, BehavioralContract, PerformanceSnapshot
from ..apip.lifecycle import APIPLifecycle
from ..apip.schema import APIP
from ..mesh.mesh import AgentMesh, MeshDisruptionScenario
from ..simulation.degradation import DegradationEngine, DegradationMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _peer_contract(now: datetime) -> BehavioralContract:
    return BehavioralContract(
        task_surface=["general"],
        metrics={
            "task_completion_rate": 0.88,
            "csat_score": 4.2,
            "policy_citation_error_rate": 0.02,
            "tool_misuse_rate": 0.01,
            "hallucination_rate": 0.03,
        },
        thresholds={
            "task_completion_rate": 0.82,
            "csat_score": 3.8,
            "policy_citation_error_rate": 0.05,
            "tool_misuse_rate": 0.04,
            "hallucination_rate": 0.06,
        },
        drift_sensitivity=2.0,
        owner="RetailCo AI Platform Team",
        created_at=now,
    )


def _snap_state(agent: BaseAgent, mesh: AgentMesh) -> dict[str, Any]:
    snap = agent.latest_snapshot()
    return {
        "agent_id": agent.agent_id,
        "agent_name": agent.agent_name,
        "health": agent.get_health_status(),
        "metrics": snap.to_metrics() if snap else {},
        "context_weight": round(mesh.context_weights.get(agent.agent_id, 0.0), 3),
        "crowding_effect": round(mesh.context_crowding_effect(agent), 3),
    }


def _crowded_snapshot(agent: BaseAgent, penalty: float, tick_offset: int) -> PerformanceSnapshot:
    p = penalty ** tick_offset
    return PerformanceSnapshot(
        timestamp=datetime.utcnow(),
        task_completion_rate=round(0.88 * p, 4),
        csat_score=round(4.2 * p, 4),
        policy_citation_error_rate=round(0.02 / p, 4),
        tool_misuse_rate=round(0.01 / p, 4),
        hallucination_rate=round(0.03 / p, 4),
        notes=f"context_crowding offset={tick_offset} cumulative_penalty={p:.3f}",
    )


# ---------------------------------------------------------------------------
# Main scenario class
# ---------------------------------------------------------------------------

class FullDemoScenario:

    @classmethod
    def run(cls) -> dict[str, Any]:
        now = datetime.utcnow()

        # ── Isolated state ────────────────────────────────────────────────────
        demo_mesh = AgentMesh()

        from ..agents.aria import aria as _aria_proto
        aria = BaseAgent("aria-001", "Aria", "customer_service", _aria_proto.contract)
        billing = BaseAgent("billing-001", "BillingAgent", "billing", _peer_contract(now))
        escalation = BaseAgent(
            "escalation-001", "EscalationAgent", "escalation", _peer_contract(now)
        )

        agents: dict[str, BaseAgent] = {
            a.agent_id: a for a in [aria, billing, escalation]
        }
        engines: dict[str, DegradationEngine] = {
            aid: DegradationEngine(a) for aid, a in agents.items()
        }

        # Add all three to mesh with equal baseline weights
        demo_mesh.add_agent(aria)
        demo_mesh.add_agent(billing, initial_weight=0.5)
        demo_mesh.add_agent(escalation, initial_weight=1 / 3)
        for aid in agents:
            demo_mesh.baseline_weights[aid] = 1.0 / 3

        timeline: list[dict[str, Any]] = []
        apip_store: dict[str, APIP | None] = {
            "aria_drift": None,
            "aria_creep": None,
            "billing": None,
            "escalation": None,
        }

        def tick_all() -> None:
            for eng in engines.values():
                eng.tick()

        def entry(tick: int, phase: str, events: list[dict]) -> dict:
            return {
                "tick": tick,
                "phase": phase,
                "events": events,
                "agents": [_snap_state(a, demo_mesh) for a in agents.values()],
            }

        def maybe_trigger(agent: BaseAgent, store_key: str) -> tuple[APIP | None, list[dict]]:
            """Check for trigger; run attribution + planning if it fires."""
            if apip_store[store_key] is not None:
                return apip_store[store_key], []

            apip = APIPLifecycle.check_trigger(agent)
            if apip is None:
                return None, []

            mode = APIPLifecycle.attribute_cause(apip, agent)
            plan = APIPLifecycle.plan_intervention(mode)
            apip.intervention_plan = plan
            APIPLifecycle.open_window(apip, 10)
            apip_store[store_key] = apip

            return apip, [
                {
                    "type": "apip_trigger",
                    "agent_id": agent.agent_id,
                    "apip_id": apip.apip_id,
                },
                {
                    "type": "attribution",
                    "failure_mode": mode.value,
                    "confidence": apip.attribution.confidence,
                    "reasoning": apip.attribution.reasoning,
                    "tier": plan.tier.value,
                    "steps": [s.description for s in plan.steps],
                },
            ]

        # ── Phase 1: ticks 1–5, healthy baseline ─────────────────────────────
        for t in range(1, 6):
            tick_all()
            timeline.append(entry(t, "healthy_baseline", []))

        # ── Phase 2: ticks 6–13, BEHAVIORAL_DRIFT injected at tick 6 ─────────
        engines[aria.agent_id].inject(DegradationMode.BEHAVIORAL_DRIFT, 0.5)

        for t in range(6, 14):
            tick_all()
            _, ev = maybe_trigger(aria, "aria_drift")
            phase = "apip_attributed" if apip_store["aria_drift"] and ev else (
                "behavioral_drift_active" if apip_store["aria_drift"] is None
                else "behavioral_drift_apip_open"
            )
            timeline.append(entry(t, phase, ev))

        # ── Phase 3: ticks 14–16, resolve drift, metrics recover ─────────────
        engines[aria.agent_id].resolve(DegradationMode.BEHAVIORAL_DRIFT)

        for t in range(14, 17):
            tick_all()
            ev: list[dict] = []
            if t == 14 and apip_store["aria_drift"]:
                ev.append({
                    "type": "intervention_applied",
                    "description": "RAG index refreshed; policy documents re-indexed.",
                    "apip_id": apip_store["aria_drift"].apip_id,
                })
            timeline.append(entry(t, "recovery", ev))

        # ── Phase 4: tick 17, check-in ────────────────────────────────────────
        tick_all()
        ev = []
        if apip_store["aria_drift"]:
            checkin = APIPLifecycle.record_checkin(
                apip_store["aria_drift"], aria.latest_snapshot()
            )
            ev.append({
                "type": "checkin",
                "trajectory": checkin.trajectory,
                "escalated": checkin.escalated,
                "apip_id": apip_store["aria_drift"].apip_id,
            })
        timeline.append(entry(17, "checkin", ev))

        # ── Phase 5: ticks 18–19, stable ─────────────────────────────────────
        for t in range(18, 20):
            tick_all()
            timeline.append(entry(t, "stable", []))

        # ── Phase 6: tick 20, exit evaluation ────────────────────────────────
        tick_all()
        ev = []
        if apip_store["aria_drift"]:
            outcome = APIPLifecycle.evaluate_exit(apip_store["aria_drift"], aria)
            ev.append({
                "type": "exit_evaluation",
                "outcome": outcome,
                "apip_id": apip_store["aria_drift"].apip_id,
            })
        timeline.append(entry(20, "exit_evaluation", ev))

        # ── Phase 7: tick 21, stable ──────────────────────────────────────────
        tick_all()
        timeline.append(entry(21, "stable", []))

        # ── Phase 8: ticks 22–29, ALIGNMENT_CREEP injected at tick 22 ────────
        engines[aria.agent_id].inject(DegradationMode.ALIGNMENT_CREEP, 0.5)

        for t in range(22, 30):
            tick_all()
            _, ev = maybe_trigger(aria, "aria_creep")
            phase = "alignment_creep_drift_trigger" if ev else (
                "alignment_creep_active" if apip_store["aria_creep"] is None
                else "alignment_creep_apip_open"
            )
            timeline.append(entry(t, phase, ev))

        # ── Phase 9: tick 30, add AgentN to mesh ─────────────────────────────
        tick_all()
        agent_n = BaseAgent(
            "agent-n-001", "AgentN", "high_performance", _peer_contract(now)
        )
        agent_n_engine = DegradationEngine(agent_n)
        for _ in range(5):
            agent_n_engine.tick()          # seed healthy baseline

        agents[agent_n.agent_id] = agent_n
        engines[agent_n.agent_id] = agent_n_engine

        demo_mesh.add_agent(agent_n, initial_weight=0.40)
        # Peers compressed: billing ~0.200, escalation ~0.200

        ev = [{
            "type": "agent_added_to_mesh",
            "agent_id": agent_n.agent_id,
            "initial_weight": 0.40,
            "peer_compression": {
                billing.agent_id: round(demo_mesh.context_weights[billing.agent_id], 3),
                escalation.agent_id: round(demo_mesh.context_weights[escalation.agent_id], 3),
            },
        }]
        timeline.append(entry(30, "mesh_disruption_start", ev))

        # ── Phase 10: ticks 31–35, peer agents degrade from crowding ─────────
        for t in range(31, 36):
            # Tick aria and agent_n normally
            engines[aria.agent_id].tick()
            engines[agent_n.agent_id].tick()

            # Override billing and escalation snapshots with crowded values
            ev = []
            for agent, store_key in [(billing, "billing"), (escalation, "escalation")]:
                penalty = demo_mesh.context_crowding_effect(agent)
                snap = _crowded_snapshot(agent, penalty, t - 30)
                agent.record_snapshot(snap)

                _, trigger_ev = maybe_trigger(agent, store_key)
                ev.extend(trigger_ev)

            timeline.append(entry(t, "peer_degradation", ev))

        # ── Phase 11: tick 36, MeshAudit ─────────────────────────────────────
        tick_all()
        audit = MeshDisruptionScenario._audit(demo_mesh, agent_n, [billing, escalation])
        ev = [{
            "type": "mesh_audit",
            "correlated_agent_id": audit.correlated_agent_id,
            "affected_agents": audit.affected_agent_ids,
            "confidence": audit.confidence,
            "recommendation": audit.recommendation,
            "compression_events": audit.compression_events,
        }]
        timeline.append(entry(36, "mesh_audit", ev))

        # ── Phase 12: tick 37, context scoping applied ────────────────────────
        tick_all()

        # Restore peer weights (simulate isolating AgentN's context buffer)
        for aid in [billing.agent_id, escalation.agent_id]:
            demo_mesh.context_weights[aid] = demo_mesh.baseline_weights[aid]
        total = sum(demo_mesh.context_weights.values())
        for aid in demo_mesh.context_weights:
            demo_mesh.context_weights[aid] /= total

        recovery_snap = PerformanceSnapshot(
            timestamp=datetime.utcnow(),
            task_completion_rate=0.88,
            csat_score=4.2,
            policy_citation_error_rate=0.02,
            tool_misuse_rate=0.01,
            hallucination_rate=0.03,
            notes="context_scoping_applied",
        )
        billing.record_snapshot(recovery_snap)
        escalation.record_snapshot(recovery_snap)

        ev = [{
            "type": "context_scoping_applied",
            "description": audit.recommendation,
            "restored_weights": {
                aid: round(demo_mesh.context_weights.get(aid, 0), 3)
                for aid in agents
            },
        }]
        for agent, store_key in [(billing, "billing"), (escalation, "escalation")]:
            apip = apip_store[store_key]
            if apip:
                outcome = APIPLifecycle.evaluate_exit(apip, agent)
                ev.append({
                    "type": "exit_evaluation",
                    "agent_id": agent.agent_id,
                    "outcome": outcome,
                    "apip_id": apip.apip_id,
                })
        timeline.append(entry(37, "context_scoping_recovery", ev))

        # ── Summary ───────────────────────────────────────────────────────────
        return {
            "total_ticks": 37,
            "phases": cls._phase_summary(timeline),
            "timeline": timeline,
            "apips": {
                k: APIPLifecycle.load(v.apip_id)
                for k, v in apip_store.items()
                if v is not None
            },
            "final_mesh": demo_mesh.status(),
        }

    @staticmethod
    def _phase_summary(timeline: list[dict]) -> list[dict]:
        phases: list[dict] = []
        current: dict | None = None

        for entry in timeline:
            phase = entry["phase"]
            if current is None or current["phase"] != phase:
                if current:
                    current["tick_end"] = entry["tick"] - 1
                    phases.append(current)
                current = {
                    "phase": phase,
                    "tick_start": entry["tick"],
                    "tick_end": entry["tick"],
                    "notable_events": [],
                }
            else:
                current["tick_end"] = entry["tick"]

            for ev in entry.get("events", []):
                current["notable_events"].append({
                    "tick": entry["tick"],
                    **ev,
                })

        if current:
            phases.append(current)

        return phases
