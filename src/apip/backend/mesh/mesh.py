from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.base_agent import BaseAgent


@dataclass
class MeshEdge:
    source_id: str
    target_id: str
    context_sharing: bool = True


@dataclass
class AgentMesh:
    agents: dict[str, "BaseAgent"] = field(default_factory=dict)
    edges: list[MeshEdge] = field(default_factory=list)

    def add_agent(self, agent: "BaseAgent", connect_to_all: bool = True) -> None:
        existing_ids = list(self.agents.keys())
        self.agents[agent.agent_id] = agent
        if connect_to_all:
            for eid in existing_ids:
                self.edges.append(MeshEdge(source_id=eid, target_id=agent.agent_id))
                self.edges.append(MeshEdge(source_id=agent.agent_id, target_id=eid))

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
                }
                for a in self.agents.values()
            ],
            "context_sharing_links": sum(1 for e in self.edges if e.context_sharing),
        }


# Singleton mesh instance
mesh = AgentMesh()
