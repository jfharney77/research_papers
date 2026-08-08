"""Pre-registration manifests.

The spec: a YAML manifest (instruments, sample, metrics, exclusion rules) is
hashed and frozen *before* simulation runs; the scoring engine refuses to
score runs whose manifest hash postdates the run. Concretely:

- `freeze_manifest` canonicalizes the manifest, hashes it, and records the
  freeze timestamp in a sidecar `.frozen.json`.
- Every run records (manifest_hash, started_at).
- `verify_run_against_manifest` rejects a run if the hash doesn't match the
  frozen manifest or the run started before the manifest was frozen.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class InstrumentSpec(BaseModel):
    """One survey instrument / behavioral measure to elicit and score."""

    name: str
    kind: str = "categorical"  # "categorical" | "continuous"
    options: list[str] = Field(default_factory=list)  # for categorical
    lo: float | None = None  # for continuous
    hi: float | None = None


class TreatmentSpec(BaseModel):
    """A known experimental effect the simulator must reproduce."""

    name: str
    instrument: str
    treatment_field: str  # persona/condition field distinguishing arms
    control_value: str
    treatment_value: str
    known_effect: float  # published effect (treatment mean - control mean)


class Manifest(BaseModel):
    name: str
    instruments: list[InstrumentSpec]
    treatments: list[TreatmentSpec] = Field(default_factory=list)
    sample_size: int
    persona_condition: str = "rich"  # e.g. "demographic" | "brief" | "rich"
    subgroup_fields: list[str] = Field(default_factory=list)  # demographic-parity axes
    exclusion_rules: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(
        default_factory=lambda: ["individual", "marginal", "treatment_effect"]
    )

    def canonical_hash(self) -> str:
        canon = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canon.encode()).hexdigest()


class FrozenRecord(BaseModel):
    manifest_hash: str
    frozen_at: str  # ISO-8601 UTC


class RunRecord(BaseModel):
    run_id: str
    manifest_hash: str
    started_at: str  # ISO-8601 UTC


def load_manifest(path: str | Path) -> Manifest:
    with Path(path).open(encoding="utf-8") as fh:
        return Manifest.model_validate(yaml.safe_load(fh))


def freeze_manifest(manifest_path: str | Path, now: datetime | None = None) -> FrozenRecord:
    """Hash the manifest and write the freeze record next to it."""
    manifest = load_manifest(manifest_path)
    record = FrozenRecord(
        manifest_hash=manifest.canonical_hash(),
        frozen_at=(now or datetime.now(timezone.utc)).isoformat(),
    )
    sidecar = Path(manifest_path).with_suffix(".frozen.json")
    sidecar.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return record


def load_frozen(manifest_path: str | Path) -> FrozenRecord:
    sidecar = Path(manifest_path).with_suffix(".frozen.json")
    if not sidecar.exists():
        raise FileNotFoundError(
            f"Manifest {manifest_path} was never frozen (missing {sidecar.name}). "
            "Pre-registration requires freeze_manifest() before any run."
        )
    return FrozenRecord.model_validate_json(sidecar.read_text(encoding="utf-8"))


def verify_run_against_manifest(run: RunRecord, manifest_path: str | Path) -> None:
    """Raise ValueError unless the run is scoreable under the frozen manifest."""
    manifest = load_manifest(manifest_path)
    frozen = load_frozen(manifest_path)
    current_hash = manifest.canonical_hash()
    if current_hash != frozen.manifest_hash:
        raise ValueError(
            "Manifest was modified after freezing "
            f"(frozen {frozen.manifest_hash[:12]}, current {current_hash[:12]}). Refusing to score."
        )
    if run.manifest_hash != frozen.manifest_hash:
        raise ValueError(
            f"Run {run.run_id} was produced under a different manifest "
            f"({run.manifest_hash[:12]} != {frozen.manifest_hash[:12]}). Refusing to score."
        )
    if datetime.fromisoformat(run.started_at) < datetime.fromisoformat(frozen.frozen_at):
        raise ValueError(
            f"Run {run.run_id} started before the manifest was frozen. Refusing to score."
        )
