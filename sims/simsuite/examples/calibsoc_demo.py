"""End-to-end CalibSoc run: freeze manifest -> simulate -> score.

Runs three simulator conditions against the synthetic panel:
  1. StubSimulator fidelity=0.85  (a "good" simulator)
  2. StubSimulator fidelity=0.30  (a demographics-only-quality simulator)
  3. LLMLoopSimulator on the stub provider (wiring proof for real models)
and prints normalized-accuracy reports, reproducing in miniature the
rich-persona vs demographics-only gap from Park et al. 2024.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from simsuite.calibsoc import (
    LLMLoopSimulator,
    PanelStore,
    ScoringEngine,
    StubSimulator,
)
from simsuite.calibsoc.manifest import RunRecord, freeze_manifest, load_manifest
from simsuite.shared.models import ModelClient

HERE = Path(__file__).parent
MANIFEST = HERE / "manifests" / "demo_manifest.yaml"
PANEL_CSV = HERE.parent / "data" / "synthetic_panel.csv"


def main() -> None:
    if not PANEL_CSV.exists():
        from make_synthetic_panel import make_panel

        PANEL_CSV.parent.mkdir(exist_ok=True)
        make_panel().to_csv(PANEL_CSV, index=False)

    # Pre-registration: freeze before any run.
    frozen = freeze_manifest(MANIFEST)
    manifest = load_manifest(MANIFEST)
    panel = PanelStore.from_csv(PANEL_CSV)
    personas = panel.personas()

    print("Human test-retest ceilings (the normalization denominators):")
    print(panel.ceiling_table(manifest.instruments).to_string(index=False))
    print()

    truth = {s.name: panel.responses(s.name, wave=1) for s in manifest.instruments}
    engine = ScoringEngine(manifest, panel, manifest_path=MANIFEST)

    conditions = {
        "rich-persona (fidelity=0.85)": StubSimulator(truth, fidelity=0.85, seed=1),
        "demographics-only (fidelity=0.30)": StubSimulator(truth, fidelity=0.30, seed=2),
        "llm-loop (stub provider)": LLMLoopSimulator(ModelClient()),
    }
    for label, sim in conditions.items():
        sim.init(personas)
        responses = {s.name: sim.elicit(s) for s in manifest.instruments}
        run = RunRecord(
            run_id=f"{label.split()[0]}-{uuid.uuid4().hex[:8]}",
            manifest_hash=frozen.manifest_hash,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        report = engine.score(run, responses, personas)
        print(f"=== {label} ===")
        print(report.summary())
        print()


if __name__ == "__main__":
    main()
