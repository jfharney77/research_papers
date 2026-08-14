# APIP paper — IEEE conference LaTeX

LaTeX conversion of `research/apip/APIP_Paper_v8_tracked.docx` into the IEEE
conference style from `ieee_agc/`.

## Build

From the repository root:

```bash
./scripts/build_apip_paper.sh            # pdflatex → bibtex → pdflatex ×2 → main.pdf
./scripts/build_apip_paper.sh --clean    # drop stale .aux/.bbl first
./scripts/build_apip_paper.sh --quiet    # summary and warnings only
```

The script reports the page count and any undefined references, undefined
citations, or overfull boxes left in `main.log`.

`IEEEtran.cls` (from `ieee_agc/latex/IEEE-conference-template-062824/`) and
`IEEEtran.bst`, `IEEEabrv.bib`, `IEEEfull.bib` (from `ieee_agc/bibtex/`) are
copied into this directory, so the build needs no TeX Live IEEE packages.

## Layout

| File | Contents |
| --- | --- |
| `main.tex` | Root document: class options, packages, title block, `\input` list |
| `sections/abstract.tex` | Abstract + `IEEEkeywords` |
| `sections/introduction.tex` | 1. Introduction |
| `sections/background.tex` | 2. Background and Related Work (2.1–2.6) |
| `sections/taxonomy.tex` | 3. A Taxonomy of Agent Failure Modes (Table I) |
| `sections/framework.tex` | 4. The APIP Framework (Fig. 1, 4.1–4.5) |
| `sections/schema.tex` | 5. Formal APIP Schema (Table II) |
| `sections/case_study.tex` | 6. Illustrative Case Study (6.1–6.3) |
| `sections/simulation.tex` | 7. Simulation-Based Evaluation (Tables III, IV) |
| `sections/open_problems.tex` | 8. Open Problems (8.1–8.4) |
| `sections/conclusion.tex` | 9. Conclusion |
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
