"""Ground-truth panel store.

Holds two-wave panel data (wave 1 = ground truth to predict, wave 2 =
re-interview of the same people) and computes the human test-retest ceiling
per instrument — the denominator of normalized accuracy, per Park et al. 2024.

Data format: long-form CSV/DataFrame with columns
    person_id, wave, instrument, response, plus arbitrary persona columns
    (age, ideology, race, ...) repeated per row.
Real GSS/ANES extracts can be melted into this shape; the demo ships a
synthetic panel generated in examples/.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from simsuite.calibsoc.manifest import InstrumentSpec

PERSONA_EXCLUDE = {"person_id", "wave", "instrument", "response"}


class PanelStore:
    def __init__(self, df: pd.DataFrame):
        required = {"person_id", "wave", "instrument", "response"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Panel is missing required columns: {sorted(missing)}")
        self.df = df

    @classmethod
    def from_csv(cls, path: str | Path) -> "PanelStore":
        return cls(pd.read_csv(path))

    def personas(self) -> pd.DataFrame:
        """One row per person with their persona attributes."""
        persona_cols = [c for c in self.df.columns if c not in PERSONA_EXCLUDE]
        return (
            self.df[self.df.wave == 1][["person_id", *persona_cols]]
            .drop_duplicates("person_id")
            .reset_index(drop=True)
        )

    def responses(self, instrument: str, wave: int) -> pd.Series:
        sub = self.df[(self.df.instrument == instrument) & (self.df.wave == wave)]
        return sub.set_index("person_id")["response"]

    def test_retest_ceiling(self, spec: InstrumentSpec) -> float:
        """Human wave-1 vs wave-2 agreement for one instrument.

        Categorical: exact-match rate. Continuous: 1 - MAE / range.
        This is the ceiling normalized accuracy divides by.
        """
        w1 = self.responses(spec.name, wave=1)
        w2 = self.responses(spec.name, wave=2)
        joined = pd.concat([w1, w2], axis=1, keys=["w1", "w2"]).dropna()
        if joined.empty:
            raise ValueError(f"No overlapping wave-1/wave-2 responses for {spec.name}")
        return _agreement(joined["w1"], joined["w2"], spec)

    def ceiling_table(self, specs: list[InstrumentSpec]) -> pd.DataFrame:
        rows = [
            {"instrument": s.name, "kind": s.kind, "ceiling": self.test_retest_ceiling(s)}
            for s in specs
        ]
        return pd.DataFrame(rows)


def _agreement(a: pd.Series, b: pd.Series, spec: InstrumentSpec) -> float:
    if spec.kind == "categorical":
        return float((a.astype(str) == b.astype(str)).mean())
    lo = spec.lo if spec.lo is not None else float(min(a.min(), b.min()))
    hi = spec.hi if spec.hi is not None else float(max(a.max(), b.max()))
    rng = hi - lo or 1.0
    mae = (a.astype(float) - b.astype(float)).abs().mean()
    return float(max(0.0, 1.0 - mae / rng))
