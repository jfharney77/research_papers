from pathlib import Path

from simsuite.divprobe import DeliberationConfig, run_deliberation
from simsuite.shared.models import ModelClient, StubProvider
from simsuite.shared.trace import TraceEvent, TraceWriter, read_trace


def test_trace_roundtrip(tmp_path: Path):
    p = tmp_path / "t.jsonl"
    events = [
        TraceEvent(episode_id="e1", agent_id="a1", turn=0, action="hello", probes={"belief": 0.7}),
        TraceEvent(episode_id="e1", agent_id="a2", turn=0, tier=2, action="hi"),
    ]
    with TraceWriter(p) as w:
        for e in events:
            w.write(e)
    back = list(read_trace(p))
    assert back == events


def test_stub_provider_deterministic():
    c = ModelClient(StubProvider())
    a = c.complete("same prompt", seed=1)
    b = c.complete("same prompt", seed=1)
    assert a == b
    assert c.complete("same prompt", seed=2)  # different seed still returns something


def test_cache_hits(tmp_path: Path):
    c = ModelClient(StubProvider(), cache_path=tmp_path / "cache.db")
    c.complete("p", seed=0)
    c.complete("p", seed=0)
    assert c.calls == 1 and c.cache_hits == 1


def test_deliberation_runs_and_traces(tmp_path: Path):
    cfg = DeliberationConfig(n_agents=6, n_rounds=3, trace_path=tmp_path / "d.jsonl")
    result = run_deliberation(cfg)
    assert len(result.rounds_texts) == 3
    assert all(len(r) == 6 for r in result.rounds_texts)
    metrics = result.metrics()
    assert len(metrics["semantic_dispersion"]) == 3
    events = list(read_trace(tmp_path / "d.jsonl"))
    assert len(events) == 18


def test_topologies_all_run():
    for topo in ("fully_connected", "small_world", "islands"):
        cfg = DeliberationConfig(n_agents=6, n_rounds=2, topology=topo)
        assert len(run_deliberation(cfg).rounds_texts) == 2
