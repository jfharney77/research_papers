# Templates

Reusable styles. Nothing here contains real paper content — the skeletons carry
placeholder text so they stay compilable, and each one is a starting point that
`scripts/new-paper.sh` copies into `papers/<slug>/latex/`.

```
templates/
  latex/ieee|neurips|acm|aaai/   conference skeletons: main.tex + sections/ + style files
  latex/_vendor/                 upstream author kits, kept verbatim for reference
  bibtex/                        shared IEEEtran .bst files and IEEE .bib abbreviations
  word/                          Word style templates (.dotx, reference.docx)
  assets/figures/                placeholder figures the skeletons reference
```

Directories under `latex/` whose name starts with an underscore are never treated
as templates by the product's template registry (`src/docbuilder/templates.py`) —
that is how `_vendor/` stays out of the picker.

## Layout of a skeleton

```
templates/latex/<conference>/
  main.tex          root document; \input{}s each section — rarely needs editing
  sections/         one file per section, so sections can be written in parallel
  references.bib
  <style files>     .cls / .sty / .bst, version-controlled per conference
```

## Verifying a template

```bash
bash scripts/templates/<conference>/build.sh
```

Do this after updating any style file — it is the fastest check that the new
`.cls`/`.sty` still compiles before a paper depends on it.

## Updating style files

| Conference | Source | Notes |
| --- | --- | --- |
| IEEE | vendored in `latex/_vendor/ieee-conference-template/` | `IEEEtran.cls`; `.bst` files live in `bibtex/` |
| NeurIPS | downloaded on first build | bump `STYLE_YEAR` / `STYLE_URL` in `scripts/templates/neurips/build.sh` annually |
| ACM | [ctan.org/pkg/acmart](https://ctan.org/pkg/acmart) | replace `acmart.cls` and the `acm*.bbx/cbx/dbx` files |
| AAAI | AAAI author kit | replace `aaai<year>.sty` / `.bst`, then bump `STYLE_YEAR` in its `build.sh` |

## Figures

`main.tex` sets a `\graphicspath` that searches, in order: the paper's own
`figures/`, then `templates/assets/figures/`. Reference images by bare filename
(`\includegraphics{ai_architecture.png}`) so a skeleton builds in place *and*
keeps building once copied into `papers/<slug>/latex/`.

Regenerate the placeholder figures with:

```bash
python sims/figures/generate_diagram.py
```
