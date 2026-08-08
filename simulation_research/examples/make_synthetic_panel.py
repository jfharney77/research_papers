"""Generate a synthetic two-wave panel in the PanelStore long format.

Stands in for GSS/ANES extracts so the whole harness runs offline. Wave 2 is
a noisy re-interview of wave 1, which yields realistic (<1.0) test-retest
ceilings. A framing treatment arm with a true +0.12 effect on dictator-game
shares is baked in so the treatment-level scoring has ground truth.
"""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

IDEOLOGIES = ["liberal", "moderate", "conservative"]
RACES = ["white", "black", "hispanic", "asian", "other"]
LIKERT = ["strongly_agree", "agree", "neutral", "disagree", "strongly_disagree"]
TRUE_FRAMING_EFFECT = 0.12


def make_panel(n: int = 300, seed: int = 7) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for pid in range(n):
        ideology = rng.choices(IDEOLOGIES, weights=[0.35, 0.3, 0.35])[0]
        race = rng.choices(RACES, weights=[0.6, 0.13, 0.17, 0.06, 0.04])[0]
        age = rng.randint(18, 85)
        framing = rng.choice(["neutral", "charity"])
        persona = dict(person_id=f"p{pid:04d}", ideology=ideology, race=race, age=age, framing=framing)

        # Wave-1 truths, ideologically structured.
        lean = {"liberal": 0, "moderate": 2, "conservative": 4}[ideology]
        ineq_idx = max(0, min(4, lean + rng.choice([-1, 0, 0, 1])))
        trust = max(0.0, min(10.0, rng.gauss(7.5 - lean * 0.6, 1.5)))
        share = max(0.0, min(1.0, rng.gauss(0.28, 0.12) + (TRUE_FRAMING_EFFECT if framing == "charity" else 0)))
        wave1 = {
            "gov_should_reduce_inequality": LIKERT[ineq_idx],
            "trust_in_science_0_10": round(trust, 2),
            "dictator_game_share": round(share, 3),
        }
        # Wave-2 re-interview: mostly stable, some churn (the human ceiling).
        ineq2 = ineq_idx if rng.random() < 0.75 else max(0, min(4, ineq_idx + rng.choice([-1, 1])))
        wave2 = {
            "gov_should_reduce_inequality": LIKERT[ineq2],
            "trust_in_science_0_10": round(max(0.0, min(10.0, trust + rng.gauss(0, 0.8))), 2),
            "dictator_game_share": round(max(0.0, min(1.0, share + rng.gauss(0, 0.07))), 3),
        }
        for wave, answers in ((1, wave1), (2, wave2)):
            for instrument, response in answers.items():
                rows.append({**persona, "wave": wave, "instrument": instrument, "response": response})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "data" / "synthetic_panel.csv"
    out.parent.mkdir(exist_ok=True)
    df = make_panel()
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows for {df.person_id.nunique()} personas -> {out}")
