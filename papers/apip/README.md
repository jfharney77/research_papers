# APIP paper — IEEE conference LaTeX

LaTeX conversion of `manuscript/APIP_Paper_v8_tracked.docx` into the IEEE
conference style.

```
manuscript/   the .docx versions and the New_Hire_Paradox.md draft
latex/        main.tex + sections/ + vendored IEEE style files  ← the build target
figures/      figures for this paper (referenced by bare filename)
deck/         APIP_Deck_v1.pptx
```

The simulation behind the case study lives in `sims/apip_sim/`; start it with
`bash scripts/papers/apip/run_sim.sh` (port 8100).

## Build

From anywhere in the repo:

```bash
bash scripts/papers/apip/build.sh            # pdflatex → bibtex → pdflatex ×2 → latex/main.pdf
bash scripts/papers/apip/build.sh --clean    # drop stale .aux/.bbl first
bash scripts/papers/apip/build.sh --quiet    # summary and warnings only
```

The script reports the page count and any undefined references, undefined
citations, or overfull boxes left in `main.log`.

`IEEEtran.cls` (from `templates/latex/_vendor/ieee-conference-template/`) and
`IEEEtran.bst`, `IEEEabrv.bib`, `IEEEfull.bib` (from `templates/bibtex/`) are
copied into `latex/`, so the build needs no TeX Live IEEE packages.

## Layout

| File | Contents |
| --- | --- |
| `latex/main.tex` | Root document: class options, packages, title block, `\input` list |
| `latex/sections/abstract.tex` | Abstract + `IEEEkeywords` |
| `latex/sections/introduction.tex` | 1. Introduction |
| `latex/sections/background.tex` | 2. Background and Related Work (2.1–2.6) |
| `latex/sections/taxonomy.tex` | 3. A Taxonomy of Agent Failure Modes (Table I) |
| `latex/sections/framework.tex` | 4. The APIP Framework (Fig. 1, 4.1–4.5) |
| `latex/sections/schema.tex` | 5. Formal APIP Schema (Table II) |
| `latex/sections/case_study.tex` | 6. Illustrative Case Study (6.1–6.3) |
| `latex/sections/simulation.tex` | 7. Simulation-Based Evaluation (Tables III, IV) |
| `latex/sections/open_problems.tex` | 8. Open Problems (8.1–8.4) |
| `latex/sections/conclusion.tex` | 9. Conclusion |
| `references.bib` | 35 entries; a comment gives each entry's number in the Word doc |

Section numbering is produced by `IEEEtran`, so the hardcoded numbers from the
Word document ("1 Introduction", "2.1 …") were dropped. Cross-references go
through `\label`/`\ref` rather than literal section numbers.

## Conversion notes

- Tracked changes in the `.docx` were **accepted** (insertions kept, deletions
  dropped) before conversion.
- Word's numeric citations `[n]` became `\cite{key}`; BibTeX renumbers them, so
  printed numbers will differ from the Word document's. All 35 references are
  cited and appear in the bibliography.
- Four citations in the Word document point at the wrong entry in its own
  reference list. They were resolved by the author name given in the sentence:
  - "support for newcomers declines within the first 90 days [6]" → Kammeyer-Mueller
    et al. (Word `[13]`), not Hendrycks. Appears twice (Sec. 2.6, Sec. 8.3).
  - "Trainer et al. [22]" → Trainer et al. (Word `[21]`), not Wegner. Also the
    later "newcomer attributes interact with team norms [22]" and the onboarding
    list "[2, 22]".
  - The TMS citation group "[23, 15, 18]" was expanded to the full canonical set
    (Wegner; Lewis et al.; Ren & Argote; Liang et al.; Moreland & Argote), which
    is also what pulls the two otherwise-uncited TMS entries into the
    bibliography.
- Section 5 refers to `mesh_context` being "described further in Section 7.3";
  that content is in the mesh subsection (Word 8.3), so the reference points
  there.
- Figure 1 (the five-phase lifecycle) is drawn with a plain `tabular` rather
  than TikZ, so the paper compiles with no packages beyond the IEEE template's.
  Replace it with a real vector figure before submission if desired.
- The title block is the double-blind placeholder from the Word document.
  Replace with `\IEEEauthorblockN`/`\IEEEauthorblockA` entries for camera-ready.
- Author-year citations inside the abstract ("Pan et al., 2025") were left as
  prose, per IEEE guidance against citations in the abstract.

Current output: 11 pages. IEEE conference limits are typically 6–8 pages, so
trimming is likely needed before submission.
