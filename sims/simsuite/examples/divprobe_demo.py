"""DivProbe demo: measure diversity collapse and test one intervention.

Runs the deliberation loop in two conditions — no persona re-injection vs
re-injection every 3 rounds — on the stub provider, and prints the four
metric trajectories side by side. On the stub, temperature and persona
prompts shift which responses are reachable, so the collapse/intervention
contrast is visible without any API spend.
"""

from __future__ import annotations

from pathlib import Path

from simsuite.divprobe import DeliberationConfig, run_deliberation

TRACES = Path(__file__).parent.parent / "data" / "traces"


def show(label: str, metrics: dict[str, list[float]]) -> None:
    print(f"--- {label} ---")
    for name, series in metrics.items():
        line = "  ".join(f"{v:6.3f}" for v in series)
        print(f"  {name:<28} {line}")
    print()


def main() -> None:
    base = dict(n_agents=12, n_rounds=8, seed=3)
    collapse_cfg = DeliberationConfig(
        **base, temperature=0.15, reinject_persona_every=0,
        trace_path=TRACES / "divprobe_collapse.jsonl",
    )
    intervention_cfg = DeliberationConfig(
        **base, temperature=0.9, persona_depth="interview", reinject_persona_every=3,
        trace_path=TRACES / "divprobe_intervention.jsonl",
    )
    print("Columns are rounds 0..7.\n")
    show("baseline (low temp, personas fade)", run_deliberation(collapse_cfg).metrics())
    show("intervention (interview personas re-injected every 3 rounds, higher temp)",
         run_deliberation(intervention_cfg).metrics())


if __name__ == "__main__":
    main()
