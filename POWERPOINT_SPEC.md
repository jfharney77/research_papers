# PowerPoint Spec — Research Paper Workspace

A spec for a slide deck that explains this project (the Word→LaTeX tool) to a technical audience.

## Goal & audience
Explain, in ~12 slides / ~10 min, what the Research Paper Workspace does, how it works, and why
its design choices matter. Audience: engineers / researchers evaluating or contributing to the tool.

## Build notes
- 16:9. Build programmatically with **python-pptx** (one function per slide, content below), or hand-author.
- This repo's sibling **`slides2video`** project can turn the finished `.pptx` into a narrated MP4.
- Pull diagrams from `MANUAL.md` and `README.md`; capture UI screenshots from the running app.

## Slide outline
1. **Title** — "Research Paper Workspace — Word → LaTeX, build, review, critique" + one-line tagline.
2. **The problem** — Turning a Word manuscript into a clean, conference-ready LaTeX/PDF is manual and
   error-prone; reviewing AI-flavored prose is ad hoc.
3. **What it is** — Upload `.docx` → per-section LaTeX → conference PDF (IEEE/NeurIPS/ACM/AAAI) →
   edit + recompile → critique. Web UI + CLI + REST API.
4. **Architecture** — `docbuilder` (converter + CLI + sandbox + template registry), `docserver`
   (FastAPI), `critic`, `web` (React/Vite); `documents/<id>/` workspaces.
5. **Conversion pipeline** — docx (python-docx) → headings split into `sections/*.tex`, figures
   extracted, `main.tex` rewritten with `\input`, build via per-conference `build.sh`.
6. **Dynamic template selection** — backend registry discovers `latex/*/` templates with build
   scripts; `GET /templates` drives the UI dropdown; add a folder → it appears automatically.
7. **Edit / recompile / export** — section editor, Recompile, build-log surfacing, LaTeX `.zip` export.
8. **The Critic** — per-section: 3 criticisms + an AI-genericness score (hybrid heuristics + LLM) +
   de-AI tips; pluggable providers (stub/claude/ollama/cerebras); ad-hoc PDF/DOCX critique.
9. **Security** — sandboxed LaTeX build (no shell-escape, restricted file IO, rlimits, timeout;
   docker mode), API-key auth, scoped CORS.
10. **Deployment** — Dockerfiles + GitHub Actions → AWS ECS Express Mode (see `DEPLOY-AWS.md`).
11. **Demo** — screenshots: upload → PDF tab → edit a section → Recompile → Critic gauge.
12. **Roadmap / closing** — reference extraction, more templates; links to `MANUAL.md` / repo.

## Assets to capture
Architecture diagram (slide 4), pipeline diagram (slide 5), 3–4 UI screenshots (PDF view, LaTeX
editor, Critic gauges, template dropdown).
