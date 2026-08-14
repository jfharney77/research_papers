# Implementation Specifications: Multi-Agent Simulation Research Projects

Engineering-level specs for building the improvements proposed in the research review. Four projects are specified in full (highest leverage, cheapest to prototype); four are specified as condensed briefs. Each full spec includes architecture, stack, data, metrics, milestones, risks, and rough cost.

---

## Project 1 — CalibSoc: A Pre-Registered Calibration Harness for LLM Social Simulators

**Objective.** A reusable open-source harness that scores any LLM population simulator against held-out human data, with a normalized-accuracy metric bounded by human test-retest reliability (extending Park et al. 2024 from individual to group level).

**Hypothesis.** Group-level predictions (opinion distributions, response to interventions) can be scored against panel data the same way individual GSS answers were, and most current simulators will clear far less of the human ceiling at group level than at individual level.

**Builds on.** Park et al. 2024 (1,052-person study), Gao et al. survey, SocioVerse alignment engines, Concordia experiment-design guide.

### Architecture
```
┌─────────────┐   ┌──────────────────┐   ┌───────────────────┐
│ Persona     │──▶│ Simulator Under  │──▶│ Outcome Extractor │
│ Loader      │   │ Test (adapter)   │   │ (survey/behavior) │
└─────────────┘   └──────────────────┘   └─────────┬─────────┘
       ▲                                           ▼
┌──────┴───────┐   ┌──────────────────┐   ┌───────────────────┐
│ Ground-Truth │──▶│ Scoring Engine   │◀──│ Pre-Registration  │
│ Panel Store  │   │ (normalized acc) │   │ Manifest (frozen) │
└──────────────┘   └──────────────────┘   └───────────────────┘
```

- **Adapter interface** (`SimulatorAdapter`): `init(personas) -> AgentPool`, `run(scenario) -> Transcript`, `elicit(instrument) -> Responses`. Ship reference adapters for Concordia, OASIS, and a plain OpenAI/Anthropic-API loop so any simulator can be plugged in with ~200 LOC.
- **Pre-registration manifest**: YAML file (instruments, sample, metrics, exclusion rules) hashed and committed *before* simulation runs; the scoring engine refuses to score runs whose manifest hash postdates the run.
- **Scoring engine**: computes `normalized_accuracy = sim_vs_human / human_vs_human_retest` at (a) individual level, (b) marginal-distribution level (Wasserstein distance on response distributions), (c) treatment-effect level (does the sim reproduce the *direction and magnitude* of a known experimental effect).

### Tech stack
Python 3.11; `pydantic` for manifests; `pandas`/`scipy` for scoring; `litellm` for model-agnostic LLM calls; DuckDB for panel storage; results as versioned Parquet + a small Streamlit report page.

### Data
- **Attitudinal ground truth**: GSS panel waves (public), World Values Survey, ANES panel (2020–2024 re-interviews give real test-retest data).
- **Behavioral ground truth**: replication packages of well-powered experiments (e.g., Many Labs 2, dictator/ultimatum meta-analytic distributions).
- **Test-retest ceilings**: computed directly from panel re-interviews; published as a lookup table per instrument.

### Metrics
Primary: normalized accuracy at the three levels above. Secondary: demographic-parity gap (accuracy variance across race/ideology subgroups, following Park 2024's bias finding); cost-per-validated-prediction.

### Milestones
1. **Weeks 1–3**: manifest schema, scoring engine, GSS/ANES ingestion, human-ceiling tables.
2. **Weeks 4–6**: three reference adapters; run demographic-persona vs. rich-persona baselines.
3. **Weeks 7–10**: full benchmark run across 3–5 models × 3 persona conditions; write-up.
4. **Stretch**: public leaderboard with mandatory manifest hashes.

### Risks & mitigations
- *Training-data contamination* (models have memorized GSS marginals): include post-cutoff panel waves and synthetic-scenario treatment effects that cannot be memorized.
- *Panel access restrictions*: ANES/GSS are public; keep restricted datasets (e.g., proprietary panels) as optional plug-ins.

**Rough cost.** ~$2–5K API spend for the full grid (1,000 personas × 5 instruments × 5 models with caching); one GPU optional for local models.

---

## Project 2 — AsymBench: An Information-Asymmetry Benchmark with Belief-State Probes

**Objective.** Turn Zhou et al.'s omniscient/non-omniscient contrast into a standardized benchmark: score agents on hidden-information social tasks *and* directly probe whether they maintain calibrated beliefs about other agents' private states.

**Builds on.** Zhou et al. (EMNLP 2024), Sotopia/SOTOPIA-Eval, Melting Pot scenario design.

### Architecture
- **Scenario compiler**: takes a scenario template (public context, per-agent private info, per-agent goals) and emits three run modes — `agents` (true asymmetry), `mindreaders` (private info shared), `script` (one model writes everyone). The gap between modes *is* the headline measurement.
- **Belief-probe injector**: at randomized turns, pauses the episode and asks the agent (out-of-band, not visible to interlocutors): "What do you believe X knows about Y? State your confidence." Probes are scored against the ground-truth information ledger the compiler maintains.
- **Information ledger**: append-only log of which facts each agent has been exposed to, enabling exact scoring of belief calibration (Brier score on "does X know fact F?").

### Task suite (v1: 60 scenarios × 3 modes)
Negotiation with hidden reservation prices; deception detection (one agent has a hidden incentive to lie); referential games with private vocabularies; cooperative planning with split blueprints; secret-keeping under social pressure (imported from Sotopia's secret dimension).

### Metrics
1. **Asymmetry gap**: goal-completion(mindreaders) − goal-completion(agents). Smaller is better.
2. **Belief calibration**: Brier score on ledger probes.
3. **Leakage rate**: private tokens surfaced in public channel (string + embedding match).
4. **Post-fine-tune transfer**: does training on `script` transcripts improve `agents`-mode performance (Zhou et al. predict: no — this is the falsifiable claim).

### Stack & data
Python; scenario templates in YAML; episode runner on top of the Sotopia codebase (Apache-2.0, reuse its evaluator); `litellm` for model coverage; human baseline via a small Prolific study (n≈60 dyads) on 10 scenarios.

### Milestones
1. **Weeks 1–2**: ledger + probe machinery on top of Sotopia.
2. **Weeks 3–5**: 60 scenarios authored + auto-validated (each must have a measurable asymmetry gap for a reference model).
3. **Weeks 6–8**: model sweep; fine-tuning transfer experiment (LoRA on an open model).
4. **Weeks 9–10**: human baseline; release.

### Risks
Probe questions may themselves teach the model to track beliefs (measurement reactivity) → run matched no-probe episodes as controls. GPT-4-as-judge bias → dual-judge + human audit on 10% sample.

**Rough cost.** ~$3K API + ~$2K human study.

---

## Project 3 — TieredSim: A Fidelity-Tiered Hybrid Simulator (LLM Core + Rule-Based Periphery)

**Objective.** A Mesa-compatible engine in which a small set of "focal" agents run full LLM reasoning while the population majority runs calibrated rule-based/statistical policies — with dynamic promotion/demotion between tiers — benchmarked on *fidelity per dollar*.

**Builds on.** Gao et al. survey (hybrid gap), OASIS (LLM + rule-based mix at 1M scale), Generative Agents (cost problem), Mesa 3, PettingZoo AEC semantics.

### Architecture
```
Tier 0  LLM agents (full memory-reflection-planning)      ~1–5% of pop
Tier 1  Distilled policy agents (small model / fitted     ~15% of pop
        behavioral model trained on Tier-0 traces)
Tier 2  Rule-based agents (classical ABM rules)           ~80% of pop
        ────────────────────────────────────────
        Promotion controller: any agent within radius r of a
        "narratively pivotal" event (defined per-domain) is promoted
        one tier for k steps; LRU demotion keeps Tier-0 budget fixed.
```
- **Scheduler**: implement as a Mesa `Model` with an AEC-style activation wrapper so the same population can also be exposed as a PettingZoo environment.
- **Distillation loop**: nightly job fits Tier-1 policies (behavior cloning on state→action pairs from Tier-0 traces; start with gradient-boosted trees over hand-crafted state features, then a 1–3B local model).
- **Consistency checks**: when an agent is demoted then re-promoted, its Tier-0 prompt is reconstructed from a compressed memory summary; measure persona drift across tier transitions.

### Evaluation
Two testbeds: (a) an opinion-dynamics scenario scored against CalibSoc (Project 1); (b) a market scenario scored against TwinMarket's stylized facts (fat tails, volatility clustering). Headline metric: **fidelity-per-dollar curves** — macro-level accuracy vs. total API+compute spend as the Tier-0 fraction sweeps 0% → 100%. The deliverable is the shape of that curve and the knee point.

### Stack
Mesa 3, `litellm`, `xgboost` → `transformers` for Tier-1, Ray for parallel episodes, DuckDB trace store.

### Milestones
1. **Weeks 1–3**: tiered scheduler + promotion controller in Mesa; all-rule and all-LLM baselines.
2. **Weeks 4–6**: distillation loop; drift metrics.
3. **Weeks 7–10**: fidelity-per-dollar sweeps on both testbeds.
4. **Stretch**: 100K-agent run reproducing an OASIS polarization result at <10% of all-LLM cost.

### Risks
Tier-1 policies may smooth away exactly the heavy-tail behaviors that matter (link to Project 4's diversity metrics — reuse them as regression tests). Promotion heuristics may bias which dynamics get high fidelity → ablate promotion rules.

**Rough cost.** ~$5–8K API for sweeps; 1×A100-class GPU for distillation.

---

## Project 4 — DivProbe: Diversity-Collapse Diagnostics and Interventions

**Objective.** A metrics package + intervention study answering: how fast do LLM agent populations homogenize, what drives it (shared base model, shared context, interaction structure), and which interventions preserve heterogeneity without destroying coherence?

**Builds on.** Diversity-collapse findings in open-ended idea generation, OASIS scale-diversity observations, SocioVerse user-pool grounding, Park 2024 interview personas.

### Metrics package (`divprobe`, pip-installable)
- **Semantic dispersion**: mean pairwise embedding distance of agent outputs per round; report as trajectory, not point estimate.
- **Opinion-distribution drift**: Wasserstein distance between round-t and round-0 stance distributions on probe questions.
- **Effective population size**: exponential of the entropy of cluster occupancy over agent outputs (how many "distinct voices" remain).
- **Structural coupling index**: partial correlation of agent outputs conditioned on the shared context window — separates "agents agree because they converged" from "agents agree because they read the same thing."

### Experimental design (factorial)
Factors: persona depth (none / demographic / interview-style) × interaction topology (fully connected / small-world / islands) × decoding (temperature, min-p) × model mix (homogeneous vs. heterogeneous model pool) × memory (shared feed vs. private memory). Outcome: metric trajectories over 50 rounds of an open-ended deliberation task + a forecasting task with a ground-truth answer (so we can check whether diversity is *useful* diversity — does preserved heterogeneity improve collective accuracy?).

### Interventions to test
Persona re-injection every k rounds; retrieval from distinct private corpora; disagreement-conditioned prompting; model-pool heterogeneity (the cheapest lever if it works); topology sparsification.

### Stack, milestones, cost
Python; runs on OASIS (Reddit-like mode) for realism + a minimal in-house loop for controlled factorials. Weeks 1–2 metrics; 3–6 factorial sweep; 7–9 intervention study; 10 release. ~$4K API.

**Key risk.** Embedding-based dispersion can be gamed by surface paraphrase diversity → pair every semantic metric with a stance/decision-level metric.

---

## Condensed Briefs (Projects 5–8)

### Project 5 — LifelongCoherence: multi-day believability benchmark
Extend LIFELONG-SOTOPIA-style episode chaining: 30 simulated days, scripted probe events at days 1/7/30 testing memory of commitments, relationships, and self-consistency. Compare memory-stream (Generative Agents), reflection-summary, RAG-over-episodes, and PIANO-style concurrent architectures under a fixed token budget. Metrics: commitment-recall F1, persona-consistency (contradiction rate via NLI over the agent's own statements), goal-completion decay slope. Stack: Sotopia runner + a scenario "director" that injects callbacks to earlier events. ~6 weeks, ~$3K.

### Project 6 — AiTM-Bench: adversarial robustness suite for agent communication
Package He et al.'s Agent-in-the-Middle attack as a reusable harness over AutoGen/Agent-Framework, CAMEL, and LangGraph topologies (chain, star, mesh). Attack budget levels: passive read, single-message tamper, persistent MITM with reflection. Defenses to benchmark: message signing/provenance headers, semantic-drift detectors (embedding distance between intended and received task state), topology hardening (verifier agents). Headline metric: attack success rate vs. task-performance overhead of each defense. ~6 weeks, ~$2K. Publish responsibly: attacks against local/open frameworks only, with defense code shipped in the same release.

### Project 7 — LLM-in-SUMO: language agents inside a validated traffic engine
Embed LLM "household" agents (departure-time and mode choice, responsive to natural-language information like transit alerts or pricing announcements) into SUMO via TraCI/Libsumo, with classical car-following untouched. Question: do LLM demand agents reproduce documented behavioral effects (e.g., asymmetric response to congestion-pricing framing) that utility-based demand models miss — or just add noise? Validate against published stated-preference and pricing natural experiments. Use Libsumo + batched async LLM calls; Tier the population per Project 3. ~10 weeks; main risk is per-step latency → make LLM decisions episodic (daily plans), not per-timestep.

### Project 8 — ScaleHarness: one agent, three scales
A thin evaluation wrapper that takes a single agent implementation (a policy + memory interface) and runs it through (a) Sotopia dyads, (b) an 8–16 agent Melting-Pot-style mixed-motive game, (c) a 1K-agent OASIS scenario — producing a three-scale scorecard. The research question: does micro-level social competence predict macro-level realism? (Every survey assumes yes; nobody has measured the correlation.) Deliverable: the cross-scale correlation matrix over 10+ agent designs. ~8 weeks, ~$5K.

---

## Shared Infrastructure Notes

- **Model access layer**: all projects use `litellm` with response caching (SQLite/Redis) — cross-project cache cuts sweep costs 30–50%.
- **Trace format**: adopt one JSONL episode schema (agent_id, tier, turn, visible_context_hash, action, probes) across all projects so Projects 1, 4, and 8 can score any run from Projects 2, 3, 5, 7.
- **Sequencing**: build 1 → 4 → 2 in parallel-friendly order (1 and 4 provide the scoring machinery that 3, 7, and 8 consume). Project 6 is fully independent and can start anytime.
- **Publication mapping**: 1 → NeurIPS D&B or ICLR; 2 → *ACL; 3 → AAMAS/ICLR; 4 → EMNLP/ICWSM; 5 → *ACL; 6 → security venue (USENIX/ACL); 7 → Transportation Research Part C or AAMAS; 8 → NeurIPS D&B.
