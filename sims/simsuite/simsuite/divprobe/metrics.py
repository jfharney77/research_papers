"""DivProbe metrics package.

Four population-heterogeneity metrics from the spec, each reported as a
per-round trajectory rather than a point estimate:

- semantic_dispersion: mean pairwise embedding distance of agent outputs.
- opinion_drift: Wasserstein distance between round-t and round-0 stance
  distributions on probe questions.
- effective_population_size: exp(entropy of cluster occupancy) — how many
  "distinct voices" remain.
- structural_coupling_index: how much of inter-agent output similarity is
  explained by the shared context they all read (separates "converged" from
  "read the same thing") — mean pairwise cosine similarity of outputs after
  regressing out the shared-context embedding, subtracted from the raw value.

Embeddings are pluggable; a dependency-free TF-IDF embedder ships as default.
The spec's key risk (paraphrase diversity gaming embedding metrics) is why
opinion_drift operates on stance/decision values, not text.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np
from scipy.stats import wasserstein_distance


class TfidfEmbedder:
    """Corpus-fitted TF-IDF vectors. Zero-dependency default embedder."""

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray | None = None

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[a-z0-9']+", text.lower())

    def fit(self, corpus: list[str]) -> "TfidfEmbedder":
        docs = [set(self._tokens(t)) for t in corpus]
        vocab_counter: Counter[str] = Counter()
        for d in docs:
            vocab_counter.update(d)
        self.vocab = {w: i for i, w in enumerate(sorted(vocab_counter))}
        n = len(docs)
        df = np.zeros(len(self.vocab))
        for d in docs:
            for w in d:
                df[self.vocab[w]] += 1
        self.idf = np.log((1 + n) / (1 + df)) + 1.0
        return self

    def embed(self, texts: list[str]) -> np.ndarray:
        assert self.idf is not None, "call fit() first"
        out = np.zeros((len(texts), len(self.vocab)))
        for i, t in enumerate(texts):
            counts = Counter(tok for tok in self._tokens(t) if tok in self.vocab)
            total = sum(counts.values()) or 1
            for w, c in counts.items():
                j = self.vocab[w]
                out[i, j] = (c / total) * self.idf[j]
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


def semantic_dispersion(embeddings: np.ndarray) -> float:
    """Mean pairwise cosine distance. Embeddings must be row-normalized."""
    n = embeddings.shape[0]
    if n < 2:
        return 0.0
    sims = embeddings @ embeddings.T
    iu = np.triu_indices(n, k=1)
    return float(np.mean(1.0 - sims[iu]))


def opinion_drift(stances_round0: np.ndarray, stances_roundt: np.ndarray) -> float:
    """Wasserstein distance between stance distributions at round 0 and round t."""
    return float(wasserstein_distance(np.asarray(stances_round0, float), np.asarray(stances_roundt, float)))


def effective_population_size(embeddings: np.ndarray, sim_threshold: float = 0.8) -> float:
    """exp(entropy) of greedy cosine-threshold cluster occupancy.

    Greedy leader clustering: each output joins the first cluster whose leader
    it is >= sim_threshold similar to, else founds a new cluster. Effective
    size = exp(Shannon entropy of the occupancy distribution); equals the true
    count when clusters are equally occupied, degrades toward 1 on collapse.
    """
    n = embeddings.shape[0]
    if n == 0:
        return 0.0
    leaders: list[int] = []
    assignment = np.empty(n, dtype=int)
    for i in range(n):
        for c, leader in enumerate(leaders):
            if float(embeddings[i] @ embeddings[leader]) >= sim_threshold:
                assignment[i] = c
                break
        else:
            leaders.append(i)
            assignment[i] = len(leaders) - 1
    occupancy = np.bincount(assignment) / n
    entropy = -float(np.sum(occupancy * np.log(occupancy + 1e-12)))
    return math.exp(entropy)


def structural_coupling_index(embeddings: np.ndarray, shared_context_embedding: np.ndarray) -> float:
    """Portion of mean pairwise similarity attributable to the shared context.

    Returns raw_similarity - residual_similarity, where residuals are the
    output embeddings after projecting out the shared-context direction.
    High values mean agents "agree because they read the same thing";
    residual similarity that stays high means genuine convergence.
    """
    n = embeddings.shape[0]
    if n < 2:
        return 0.0
    c = np.asarray(shared_context_embedding, float)
    c_norm = np.linalg.norm(c)
    if c_norm == 0:
        return 0.0
    c = c / c_norm
    raw = _mean_pairwise_cosine(embeddings)
    residuals = embeddings - np.outer(embeddings @ c, c)
    norms = np.linalg.norm(residuals, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    residuals = residuals / norms
    return float(raw - _mean_pairwise_cosine(residuals))


def _mean_pairwise_cosine(x: np.ndarray) -> float:
    sims = x @ x.T
    iu = np.triu_indices(x.shape[0], k=1)
    return float(np.mean(sims[iu]))


def diversity_report(
    rounds_texts: list[list[str]],
    rounds_stances: list[np.ndarray] | None = None,
    shared_contexts: list[str] | None = None,
    embedder: TfidfEmbedder | None = None,
) -> dict[str, list[float]]:
    """Full metric trajectories for a multi-round population run.

    rounds_texts[t] = list of agent outputs at round t. Optional per-round
    stance arrays and shared-context strings enable the drift and coupling
    metrics. Returns {metric_name: [value per round]}.
    """
    all_texts = [t for r in rounds_texts for t in r] + list(shared_contexts or [])
    emb = embedder or TfidfEmbedder().fit(all_texts)
    report: dict[str, list[float]] = {
        "semantic_dispersion": [],
        "effective_population_size": [],
    }
    if rounds_stances is not None:
        report["opinion_drift"] = []
    if shared_contexts is not None:
        report["structural_coupling_index"] = []

    for t, texts in enumerate(rounds_texts):
        vecs = emb.embed(texts)
        report["semantic_dispersion"].append(semantic_dispersion(vecs))
        report["effective_population_size"].append(effective_population_size(vecs))
        if rounds_stances is not None:
            report["opinion_drift"].append(opinion_drift(rounds_stances[0], rounds_stances[t]))
        if shared_contexts is not None:
            ctx_vec = emb.embed([shared_contexts[t]])[0]
            report["structural_coupling_index"].append(structural_coupling_index(vecs, ctx_vec))
    return report
