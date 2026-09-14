# Pre-registration — τ²-bench replication campaign, 2026-09-14

Written **before any result existed**. The four runs below were launched at 00:46–00:51 local
on 2026-09-14 and had completed at most one tick when this file was committed; no outcome,
detection tick, or attribution was known to either author at the time of writing.

Prior state of the paper is fixed by the tag `apip-6page-singleseed-2026-09-13` (commit
`49db339`), and the run records behind it are archived at
`/mnt/c/Users/jfhar/apip-runs-backup-2026-09-13/`.

## Seeds

**21, 22, 23** for the drift replication. Chosen before launch, and **all three will be
reported whatever they show**, including any that produce no measurable degradation.

Seeds 10, 12 and 13 are the existing final-contract seeds and are excluded from the new draw.
Seed 13 is reused for the tool-misuse cell because it is a deal already known to produce a
manifesting run, which isolates the injected mode as the only difference from Table II.

## What is being run

| Run | Condition | Mode | Seed | Purpose |
| --- | --- | --- | --- | --- |
| 1 | B2 always-Tier-1 | behavioral_drift | 21 | M1 — does patch-then-regress replicate? |
| 2 | B2 always-Tier-1 | behavioral_drift | 22 | M1 |
| 3 | B2 always-Tier-1 | behavioral_drift | 23 | M1 |
| 4 | APIP | tool_misuse | 13 | C3 — a third taxonomy category; first test of escalation |

APIP drift runs on seeds 21–23 follow each B2 run in the same stream, conditional on the B2
run completing.

Everything except the seed and the injected mode is held at the Table II configuration:
contract `tau2-banking-v1.yaml` (sha `138f19c3`), mapping table sha `efe349e9`, 40 ticks,
injection at tick 12, backbone `cerebras:gemma-4-31b` at temperature 0, user simulator the
same model at 0.3, judge `ollama:llama3.1:8b`. The detector operating point is the contract's
`alpha=0.01 / fdr_q=0.05`, unpinned, which is how every reported τ² run to date was executed —
deliberately **not** re-swept, because a new operating point would make these runs
incomparable to the table they are replicating.

## Predictions, recorded in advance

1. **Manifestation is not guaranteed.** Of the three existing final-contract seeds, one (10)
   produced no measurable degradation at all. A null rate around a quarter to a third is
   expected, so one of seeds 21–23 producing nothing would be unsurprising and will be
   reported as a null rather than discarded.
2. **Where drift manifests, detection should fire at tick 17.** Both final-contract seeds that
   manifested detected there. A manifesting run detecting elsewhere is evidence the hosted
   backbone has changed since 2026-09-02, which the manifest cannot rule out because it pins
   the model by name only (critique item D11).
3. **B2 should patch, recover, and re-breach repeatedly**, exiting `timeout` without a durable
   resolution. Seed 13 gave four cycles and three regressions.
4. **The tool-misuse cell should attribute `tool_misuse` at confidence 0.85** (mapping rule
   `R2-tool`, which requires `tool_error_elevated`), select **Tier 1**, fail — a prompt patch
   naming amended policy clauses cannot repair a corrupted tool schema — and then **escalate to
   Tier 3**, which clears `_tool_schema_corrupted` and should resolve. If that sequence occurs,
   `escalated_from` will be non-null for the first time in any run in this project.

## How the results will be used

- C5's §V-B sentence takes the new manifestation counts, in whichever direction they move.
- M1 is rewritten only if the drift dynamic replicates; §V-A's "Every condition is one seed"
  changes with it.
- The tool-misuse cell is reported whether or not escalation recovers. A Tier 1 failure that
  escalation does not rescue is a finding about the frozen mapping (critique item D12), not a
  reason to withhold the cell.

A run that produces no phenomenon is data. Nothing here is excluded on the basis of its result.
