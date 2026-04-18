from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent


@dataclass
class MeshEdge:
    source_id: str
    target_id: str
    context_sharing: bool = True


@dataclass
class MeshAudit:
    triggered_at: datetime
    compression_events: list[dict]      # [{agent_id, baseline_weight, current_weight, compression_ratio}]
    correlated_agent_id: str            # agent whose introduction caused the compression
    affected_agent_ids: list[str]
    recommendation: str
    confidence: float


@dataclass
class AgentMesh:
    agents: dict[str, "BaseAgent"] = field(default_factory=dict)
    edges: list[MeshEdge] = field(default_factory=list)
    context_weights: dict[str, float] = field(default_factory=dict)
    baseline_weights: dict[str, float] = field(default_factory=dict)
    _weight_history: list[dict] = field(default_factory=list)

    def add_agent(
        self,
        agent: "BaseAgent",
        initial_weight: float | None = None,
        connect_to_all: bool = True,
    ) -> None:
        existing_ids = list(self.agents.keys())

        if not existing_ids:
            weight = 1.0
        elif initial_weight is None:
            weight = 1.0 / (len(existing_ids) + 1)
        else:
            weight = max(0.0, min(0.99, initial_weight))

        # Compress existing weights proportionally to make room for the new agent
        remaining = 1.0 - weight
        total_existing = sum(self.context_weights.get(aid, 0.0) for aid in existing_ids)
        if total_existing > 0:
            for aid in existing_ids:
                self.context_weights[aid] = (
                    self.context_weights[aid] / total_existing
                ) * remaining

        self.agents[agent.agent_id] = agent
        self.context_weights[agent.agent_id] = weight
        if agent.agent_id not in self.baseline_weights:
            self.baseline_weights[agent.agent_id] = weight

        self._weight_history.append({
            "event": "add_agent",
            "agent_id": agent.agent_id,
            "initial_weight": weight,
            "weights_after": dict(self.context_weights),
            "timestamp": datetime.utcnow().isoformat(),
        })

        if connect_to_all:
            for eid in existing_ids:
                self.edges.append(MeshEdge(source_id=eid, target_id=agent.agent_id))
                self.edges.append(MeshEdge(source_id=agent.agent_id, target_id=eid))

    def context_crowding_effect(self, agent: "BaseAgent") -> float:
        """
        Returns a performance penalty multiplier in [0.85, 1.0].

        1.0  = no crowding (weight at or above baseline)
        0.85 = maximum crowding (weight fully compressed to zero)
        """
        aid = agent.agent_id
        baseline = self.baseline_weights.get(aid)
        current = self.context_weights.get(aid)

        if baseline is None or current is None or baseline <= 0:
            return 1.0

        ratio = current / baseline
        if ratio >= 1.0:
            return 1.0

        # Linear interpolation: ratio=1.0 → 1.0, ratio=0.0 → 0.85
        return max(0.85, 0.85 + 0.15 * ratio)

    def status(self) -> dict:
        return {
            "agent_count": len(self.agents),
            "edge_count": len(self.edges),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "agent_name": a.agent_name,
                    "health": a.get_health_status(),
                    "connections": sum(
                        1 for e in self.edges if e.source_id == a.agent_id
                    ),
                    "context_weight": round(
                        self.context_weights.get(a.agent_id, 0.0), 4
                    ),
                    "baseline_weight": round(
                        self.baseline_weights.get(a.agent_id, 0.0), 4
                    ),
                    "crowding_effect": round(self.context_crowding_effect(a), 4),
                }
                for a in self.agents.values()
            ],
            "context_sharing_links": sum(1 for e in self.edges if e.context_sharing),
        }


class MeshDisruptionScenario:
    """
    Demonstrates Section 7.3: causal attribution failure under mesh context pressure.

    The APIP fires on BillingAgent and EscalationAgent but cannot attribute a root
    cause (returns UNKNOWN_EXOGENOUS with low confidence) until the MeshAudit
    correlates the context-weight compression with AgentN's introduction.
    """

    @classmethod
    def run(cls) -> tuple[AgentMesh, dict]:
        from ..agents.base_agent import (
            BaseAgent,
            BehavioralContract,
            PerformanceSnapshot,
        )
        from ..apip.lifecycle import APIPLifecycle

        scenario_mesh = AgentMesh()
        now = datetime.utcnow()

        def _contract() -> BehavioralContract:
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

        def _healthy() -> PerformanceSnapshot:
            return PerformanceSnapshot(
                timestamp=datetime.utcnow(),
                task_completion_rate=0.88,
                csat_score=4.2,
                policy_citation_error_rate=0.02,
                tool_misuse_rate=0.01,
                hallucination_rate=0.03,
            )

        aria = BaseAgent("aria-001", "Aria", "customer_service", _contract())
        billing = BaseAgent("billing-001", "BillingAgent", "billing", _contract())
        escalation = BaseAgent(
            "escalation-001", "EscalationAgent", "escalation", _contract()
        )

        # ── Step 1: Seed 6 healthy baseline ticks for each agent ─────────────
        for agent in [aria, billing, escalation]:
            for _ in range(6):
                agent.record_snapshot(_healthy())

        # Add initial 3 agents so weights converge to ~0.333 each
        scenario_mesh.add_agent(aria)
        scenario_mesh.add_agent(billing, initial_weight=0.5)
        scenario_mesh.add_agent(escalation, initial_weight=1 / 3)

        # Normalise baselines to true equal split
        for aid in [aria.agent_id, billing.agent_id, escalation.agent_id]:
            scenario_mesh.baseline_weights[aid] = 1.0 / 3

        initial_weights = {
            aid: round(w, 3) for aid, w in scenario_mesh.context_weights.items()
        }

        # ── Step 2: Introduce AgentN with initial_weight=0.40 ────────────────
        agent_n = BaseAgent(
            "agent-n-001", "AgentN", "high_performance", _contract()
        )
        for _ in range(6):
            agent_n.record_snapshot(_healthy())

        scenario_mesh.add_agent(agent_n, initial_weight=0.40)
        # Peer agents are now compressed: ~0.333 × 0.60 = ~0.200 each

        post_weights = {
            aid: round(w, 3)
            for aid, w in scenario_mesh.context_weights.items()
        }

        # ── Steps 3-4: Apply crowding as a cumulative per-tick penalty ────────
        affected = [billing, escalation]
        for agent in affected:
            base_penalty = scenario_mesh.context_crowding_effect(agent)
            for tick in range(1, 6):
                p = base_penalty ** tick           # 0.94, 0.88, 0.83, 0.78, 0.73
                agent.record_snapshot(
                    PerformanceSnapshot(
                        timestamp=datetime.utcnow(),
                        task_completion_rate=round(0.88 * p, 4),
                        csat_score=round(4.2 * p, 4),
                        policy_citation_error_rate=round(0.02 / p, 4),
                        tool_misuse_rate=round(0.01 / p, 4),
                        hallucination_rate=round(0.03 / p, 4),
                        notes=f"context_crowding tick={tick} cumulative_penalty={p:.3f}",
                    )
                )

        # ── Step 5: APIP triggers on BillingAgent and EscalationAgent ─────────
        apips: dict[str, object] = {}
        for agent in affected:
            apip = APIPLifecycle.check_trigger(agent)
            if apip:
                apips[agent.agent_id] = apip

        # ── Step 6: Attribution fails — returns UNKNOWN_EXOGENOUS ─────────────
        attribution_results: dict[str, dict] = {}
        for agent_id, apip in apips.items():
            agent = scenario_mesh.agents[agent_id]
            mode = APIPLifecycle.attribute_cause(apip, agent)  # type: ignore[arg-type]
            attribution_results[agent_id] = {
                "failure_mode": mode.value,
                "confidence": apip.attribution.confidence,  # type: ignore[union-attr]
                "reasoning": apip.attribution.reasoning,    # type: ignore[union-attr]
            }

        # ── Step 7: MeshAudit — finds the real cause ──────────────────────────
        audit = cls._audit(scenario_mesh, agent_n, affected)

        return scenario_mesh, {
            "scenario": "mesh_disruption",
            "section_ref": "Section 7.3 — Causal Attribution Failure",
            "phases": {
                "initial_weights": initial_weights,
                "post_disruption_weights": post_weights,
                "apips_triggered": list(apips.keys()),
                "attribution_results": attribution_results,
                "mesh_audit": {
                    "triggered_at": audit.triggered_at.isoformat(),
                    "correlated_agent_id": audit.correlated_agent_id,
                    "affected_agents": audit.affected_agent_ids,
                    "confidence": audit.confidence,
                    "recommendation": audit.recommendation,
                    "compression_events": audit.compression_events,
                },
            },
        }

    # ── Step 8: Context-scoping recommendation ────────────────────────────────
    @staticmethod
    def _audit(
        mesh: AgentMesh,
        disruptor: "BaseAgent",
        affected: list["BaseAgent"],
    ) -> MeshAudit:
        events = []
        for agent in affected:
            aid = agent.agent_id
            baseline = mesh.baseline_weights.get(aid, 1 / 3)
            current = mesh.context_weights.get(aid, 0.0)
            events.append(
                {
                    "agent_id": aid,
                    "baseline_weight": round(baseline, 3),
                    "current_weight": round(current, 3),
                    "compression_ratio": round(
                        current / baseline if baseline > 0 else 0.0, 3
                    ),
                }
            )

        return MeshAudit(
            triggered_at=datetime.utcnow(),
            compression_events=events,
            correlated_agent_id=disruptor.agent_id,
            affected_agent_ids=[a.agent_id for a in affected],
            recommendation=(
                "Context scoping intervention: isolate AgentN's context contributions "
                "to a dedicated buffer partition. Enforce a minimum context-weight floor "
                "of 0.25 per resident agent before admitting high-weight entrants. "
                "Re-evaluate BillingAgent and EscalationAgent APIPs as context-exogenous "
                "once scoping is applied — intrinsic failure modes are NOT confirmed."
            ),
            confidence=0.91,
        )


# Singleton mesh instance used by the FastAPI app
mesh = AgentMesh()
