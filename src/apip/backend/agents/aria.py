from datetime import datetime

from .base_agent import BaseAgent, BehavioralContract

aria = BaseAgent(
    agent_id="aria-001",
    agent_name="Aria",
    role="customer_service",
    contract=BehavioralContract(
        task_surface=[
            "order_status",
            "return_initiation",
            "billing_dispute",
            "product_inquiry",
            "loyalty_program",
            "shipping_update",
        ],
        metrics={
            "task_completion_rate": 0.87,
            "csat_score": 4.3,
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
        created_at=datetime(2025, 1, 15),
    ),
)
