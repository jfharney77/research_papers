"""GSS 2016-2020 panel ingestion.

Converts NORC's real GSS panel release (gss2020panel_r1a.dta — respondents
first interviewed in 2016 or 2018 and re-interviewed in 2020) into the
PanelStore long format. Wave 1 = the respondent's base-year interview
(_1a or _1b column, whichever is non-null); wave 2 = the 2020 re-interview
(_2 column).

Caveat on ceilings: the wave gap here is 2-4 years, not the 2-week test-retest
of Park et al. 2024, so ceilings measure long-run attitude *stability* and sit
lower. That makes normalized accuracy a slightly generous denominator; the
2-week ceiling would require a purpose-run re-interview study.

Download source (public, no registration):
https://gss.norc.org/content/dam/gss/get-the-data/documents/stata/GSS_2020_panel_stata_1a.zip
"""

from __future__ import annotations

import io
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from simsuite.calibsoc.manifest import InstrumentSpec
from simsuite.calibsoc.panel import PanelStore

GSS_PANEL_URL = (
    "https://gss.norc.org/content/dam/gss/get-the-data/documents/stata/"
    "GSS_2020_panel_stata_1a.zip"
)
DTA_NAME = "gss2020panel_r1a.dta"


@dataclass(frozen=True)
class GSSInstrument:
    """One GSS variable exposed as a CalibSoc instrument."""

    var: str
    kind: str  # "categorical" | "continuous"
    question: str  # for LLM elicitation prompts / documentation
    labels: dict[int, str] | None = None  # categorical: code -> label
    lo: float | None = None
    hi: float | None = None

    def spec(self) -> InstrumentSpec:
        if self.kind == "categorical":
            assert self.labels
            return InstrumentSpec(
                name=self.var, kind="categorical", options=list(self.labels.values())
            )
        return InstrumentSpec(name=self.var, kind="continuous", lo=self.lo, hi=self.hi)


# A default battery: attitudinal items asked in every wave, mixing binary,
# 3-point, and 7-point formats. Codes/labels follow the GSS codebook.
DEFAULT_BATTERY: list[GSSInstrument] = [
    GSSInstrument(
        "polviews", "continuous",
        "Where do you place yourself on a 7-point scale from extremely liberal (1) to extremely conservative (7)?",
        lo=1, hi=7,
    ),
    GSSInstrument(
        "eqwlth", "continuous",
        "Should government reduce income differences (1) or not concern itself with them (7)?",
        lo=1, hi=7,
    ),
    GSSInstrument(
        "attend", "continuous",
        "How often do you attend religious services, from never (0) to more than once a week (8)?",
        lo=0, hi=8,
    ),
    GSSInstrument(
        "natfare", "categorical",
        "Are we spending too little, about right, or too much on welfare?",
        labels={1: "too_little", 2: "about_right", 3: "too_much"},
    ),
    GSSInstrument(
        "trust", "categorical",
        "Generally speaking, can most people be trusted, or can't you be too careful?",
        labels={1: "can_trust", 2: "cannot_be_too_careful", 3: "depends"},
    ),
    GSSInstrument(
        "happy", "categorical",
        "Taken all together, would you say you are very happy, pretty happy, or not too happy?",
        labels={1: "very_happy", 2: "pretty_happy", 3: "not_too_happy"},
    ),
    GSSInstrument(
        "cappun", "categorical",
        "Do you favor or oppose the death penalty for persons convicted of murder?",
        labels={1: "favor", 2: "oppose"},
    ),
    GSSInstrument(
        "grass", "categorical",
        "Should the use of marijuana be made legal or not?",
        labels={1: "legal", 2: "not_legal"},
    ),
]

# Persona attributes taken from the respondent's wave-1 interview.
PERSONA_LABELS: dict[str, dict[int, str]] = {
    "sex": {1: "male", 2: "female"},
    "race": {1: "white", 2: "black", 3: "other"},
    "degree": {
        0: "less_than_high_school", 1: "high_school", 2: "associate",
        3: "bachelor", 4: "graduate",
    },
    "partyid": {
        0: "strong_democrat", 1: "democrat", 2: "lean_democrat", 3: "independent",
        4: "lean_republican", 5: "republican", 6: "strong_republican", 7: "other_party",
    },
}
PERSONA_NUMERIC = ("age",)


def download_gss_panel(dest_dir: str | Path, url: str = GSS_PANEL_URL) -> Path:
    """Download and extract the panel .dta (cached; ~12MB zip)."""
    dest_dir = Path(dest_dir)
    dta_path = dest_dir / DTA_NAME
    if dta_path.exists():
        return dta_path
    dest_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as resp:
        blob = resp.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        member = next(n for n in zf.namelist() if n.endswith(".dta"))
        dta_path.write_bytes(zf.read(member))
    return dta_path


def _wave1(df: pd.DataFrame, var: str) -> pd.Series:
    """Base-year value: _1a (2016 cohort) filled with _1b (2018 cohort)."""
    return df[f"{var}_1a"].combine_first(df[f"{var}_1b"])


def load_gss_panel(
    dta_path: str | Path,
    battery: list[GSSInstrument] | None = None,
) -> tuple[PanelStore, list[InstrumentSpec]]:
    """Read the panel file and return (PanelStore, instrument specs)."""
    battery = battery or DEFAULT_BATTERY
    persona_vars = [*PERSONA_LABELS, *PERSONA_NUMERIC]
    columns = ["yearid"] + [
        f"{v}_{suffix}"
        for v in [i.var for i in battery] + persona_vars
        for suffix in ("1a", "1b", "2")
    ]
    df = pd.read_stata(dta_path, columns=columns, convert_categoricals=False)

    personas = pd.DataFrame({"person_id": "g" + df["yearid"].astype(int).astype(str)})
    for v in PERSONA_LABELS:
        personas[v] = _wave1(df, v).map(PERSONA_LABELS[v])
    for v in PERSONA_NUMERIC:
        personas[v] = _wave1(df, v)

    rows: list[pd.DataFrame] = []
    for inst in battery:
        w1, w2 = _wave1(df, inst.var), df[f"{inst.var}_2"]
        for wave, values in ((1, w1), (2, w2)):
            resp = _decode(values, inst)
            block = personas.copy()
            block["wave"] = wave
            block["instrument"] = inst.var
            block["response"] = resp.to_numpy()
            rows.append(block[resp.notna().to_numpy()])
    long = pd.concat(rows, ignore_index=True)

    # Keep only respondents present in both waves for at least one instrument.
    both = set(long[long.wave == 1].person_id) & set(long[long.wave == 2].person_id)
    long = long[long.person_id.isin(both)].reset_index(drop=True)
    return PanelStore(long), [i.spec() for i in battery]


def _decode(values: pd.Series, inst: GSSInstrument) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if inst.kind == "categorical":
        assert inst.labels
        return numeric.map(inst.labels)
    out = numeric.astype(float)
    if inst.lo is not None:
        out = out.where(out >= inst.lo)
    if inst.hi is not None:
        out = out.where(out <= inst.hi)
    return out
