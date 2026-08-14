# Papers

One directory per paper. Content only — styles live in `templates/`, code lives
in `sims/`, and build commands live in `scripts/papers/<slug>/`.

```
papers/<slug>/
  manuscript/   .docx / .md source material, including tracked-changes versions
  latex/        main.tex + sections/ + any vendored style files — the build target
  figures/      this paper's figures; referenced by bare filename via \graphicspath
  deck/         slides
  README.md     what the paper is, how to build it, section-by-section layout
```

| Paper | Subject |
| --- | --- |
| [`apip/`](apip/) | "Your Agent is Underperforming: The Case for Agent Performance Improvement Plans" (the New Hire Paradox) |

## Adding one

```bash
bash scripts/new-paper.sh <slug> [conference]     # conference defaults to ieee
```

This creates the directories above *and* `scripts/papers/<slug>/build.sh`, so the
two trees stay in step. Then:

```bash
bash scripts/papers/<slug>/build.sh
```

Build artifacts (`.aux`, `.bbl`, `main.pdf`, …) are gitignored repo-wide — commit
sources, not output.
