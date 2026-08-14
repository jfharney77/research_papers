from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from simsuite.calibsoc.manifest import (
    RunRecord,
    freeze_manifest,
    load_manifest,
    verify_run_against_manifest,
)

MANIFEST_YAML = {
    "name": "t",
    "sample_size": 10,
    "instruments": [{"name": "q1", "kind": "categorical", "options": ["a", "b"]}],
}


@pytest.fixture
def manifest_path(tmp_path: Path) -> Path:
    p = tmp_path / "m.yaml"
    p.write_text(yaml.safe_dump(MANIFEST_YAML))
    return p


def _run(manifest_hash: str, started_at: datetime) -> RunRecord:
    return RunRecord(run_id="r1", manifest_hash=manifest_hash, started_at=started_at.isoformat())


def test_freeze_then_valid_run_passes(manifest_path: Path):
    frozen = freeze_manifest(manifest_path)
    later = datetime.fromisoformat(frozen.frozen_at) + timedelta(minutes=1)
    verify_run_against_manifest(_run(frozen.manifest_hash, later), manifest_path)


def test_run_before_freeze_rejected(manifest_path: Path):
    frozen = freeze_manifest(manifest_path)
    earlier = datetime.fromisoformat(frozen.frozen_at) - timedelta(minutes=1)
    with pytest.raises(ValueError, match="before the manifest was frozen"):
        verify_run_against_manifest(_run(frozen.manifest_hash, earlier), manifest_path)


def test_modified_manifest_rejected(manifest_path: Path):
    frozen = freeze_manifest(manifest_path)
    changed = dict(MANIFEST_YAML, sample_size=99)
    manifest_path.write_text(yaml.safe_dump(changed))
    later = datetime.fromisoformat(frozen.frozen_at) + timedelta(minutes=1)
    with pytest.raises(ValueError, match="modified after freezing"):
        verify_run_against_manifest(_run(frozen.manifest_hash, later), manifest_path)


def test_unfrozen_manifest_rejected(manifest_path: Path):
    m = load_manifest(manifest_path)
    now = datetime.now(timezone.utc)
    with pytest.raises(FileNotFoundError, match="never frozen"):
        verify_run_against_manifest(_run(m.canonical_hash(), now), manifest_path)


def test_hash_is_stable_across_key_order(tmp_path: Path):
    a = load_manifest_from(tmp_path, "a.yaml", MANIFEST_YAML)
    reordered = {k: MANIFEST_YAML[k] for k in reversed(list(MANIFEST_YAML))}
    b = load_manifest_from(tmp_path, "b.yaml", reordered)
    assert a.canonical_hash() == b.canonical_hash()


def load_manifest_from(tmp_path: Path, name: str, data: dict):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(data))
    return load_manifest(p)
