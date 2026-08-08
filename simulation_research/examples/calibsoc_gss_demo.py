"""CalibSoc on real GSS 2016-2020 panel data.

Downloads NORC's public panel release (cached under data/raw/), melts it into
the PanelStore long format, computes real human stability ceilings, freezes a
pre-registration manifest, and scores three simulator conditions against the
actual wave-1 responses of ~3,000 re-interviewed Americans.

Note: with a 2-4 year wave gap the ceiling measures attitude stability, not
2-week test-retest reliability — see simsuite/calibsoc/gss.py docstring.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from simsuite.calibsoc import LLMLoopSimulator, ScoringEngine, StubSimulator
from simsuite.calibsoc.gss import DEFAULT_BATTERY, download_gss_panel, load_gss_panel
from simsuite.calibsoc.manifest import Manifest, RunRecord, freeze_manifest, load_manifest
from simsuite.shared.models import ModelClient

HERE = Path(__file__).parent
RAW_DIR = HERE.parent / "data" / "raw"
PANEL_CSV = HERE.parent / "data" / "gss_panel.csv"
MANIFEST = HERE / "manifests" / "gss_manifest.yaml"


def build_manifest(sample_size: int) -> None:
    """Write the GSS manifest from the battery (only if absent — it gets frozen)."""
    if MANIFEST.exists():
        return
    manifest = Manifest(
        name="gss-2016-2020-panel-battery",
        sample_size=sample_size,
        persona_condition="demographic",
        subgroup_fields=["race", "partyid"],
        instruments=[inst.spec() for inst in DEFAULT_BATTERY],
        exclusion_rules=["respondents missing both wave responses are dropped per instrument"],
    )
    MANIFEST.write_text(yaml.safe_dump(manifest.model_dump(), sort_keys=False), encoding="utf-8")


def main() -> None:
    dta = download_gss_panel(RAW_DIR)
    panel, specs = load_gss_panel(dta)
    panel.df.to_csv(PANEL_CSV, index=False)
    personas = panel.personas()
    print(f"GSS panel loaded: {len(personas)} re-interviewed respondents, {len(specs)} instruments")

    build_manifest(sample_size=len(personas))
    frozen = freeze_manifest(MANIFEST)
    manifest = load_manifest(MANIFEST)

    print("\nReal human stability ceilings (wave 1 -> 2020 re-interview):")
    print(panel.ceiling_table(manifest.instruments).to_string(index=False))

    truth = {s.name: panel.responses(s.name, wave=1) for s in manifest.instruments}
    engine = ScoringEngine(manifest, panel, manifest_path=MANIFEST)
    conditions = {
        "oracle-persona (fidelity=0.85)": StubSimulator(truth, fidelity=0.85, seed=1),
        "weak-persona (fidelity=0.30)": StubSimulator(truth, fidelity=0.30, seed=2),
        "llm-loop (stub provider)": LLMLoopSimulator(ModelClient()),
    }
    for label, sim in conditions.items():
        sim.init(personas)
        responses = {s.name: sim.elicit(s) for s in manifest.instruments}
        run = RunRecord(
            run_id=f"gss-{uuid.uuid4().hex[:8]}",
            manifest_hash=frozen.manifest_hash,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        print(f"\n=== {label} ===")
        print(engine.score(run, responses, personas).summary())


if __name__ == "__main__":
    main()
