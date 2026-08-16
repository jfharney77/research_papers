# Spec: Converter Output Targeting (write LaTeX into a paper directory)

**Status:** Proposed
**Scope:** An explicit output directory for `convert_document`, exposed on the CLI only.
CLI `--overwrite`. A collision policy for existing paper LaTeX. Template-artifact
filtering in `_copy_template`. Retirement of `scripts/word_to_latex.sh`.
**Branch:** implement on `devel-reorg`.

---

## 1. Summary & Goal

After the reorg, a paper's LaTeX lives in `papers/<slug>/latex/` and is built by
`scripts/papers/<slug>/build.sh`. The converter cannot write there. `convert_document()`
computes its own destination and always lands in `documents/<id>/<template>/`, which is
the docserver's gitignored runtime scratch directory.

**Goal:** let the caller say where the converted LaTeX goes. `ConversionOptions` gains an
output directory; the Typer CLI gains `--out` and `--overwrite`; the HTTP API deliberately
gains neither. With that in place, converting a manuscript into its own paper directory is
one command and `scripts/word_to_latex.sh` — currently a 159-line shell workaround —
becomes unnecessary.

---

## 2. Current Behavior (as-is)

`convert_document()` (`src/docbuilder/converter.py:35`) derives everything from the input
filename:

```python
document_id = snake_case(docx_path.stem)
workspace = DOCUMENTS_ROOT / document_id
...
template_workspace = workspace / options.template
_copy_template(template_dir, template_workspace)
```

`DOCUMENTS_ROOT` is `REPO_ROOT / "documents"` (`src/docbuilder/config.py:10`) and is
gitignored (`.gitignore:8`). The layout it produces is a *workspace* — the stored `.docx`,
`manifest.json`, and a `<template>/` subdirectory — not the flat `main.tex + sections/`
layout a paper directory wants. There is no parameter, environment variable, or CLI flag
that moves any of it.

| Layer | File | Relevant behavior |
|-------|------|-------------------|
| Options | `converter.py` → `ConversionOptions` | `template`, `build_pdf`, `overwrite`. No destination. |
| Converter | `converter.py` → `convert_document()` | Hardcodes `DOCUMENTS_ROOT / snake_case(stem)`; raises `ConversionError` if it exists and `overwrite` is false. |
| Template copy | `converter.py` → `_copy_template()` | `shutil.copytree(template_dir, destination)`, then deletes placeholder `sections/*.tex`. Copies everything else verbatim. |
| CLI | `cli.py` → `convert()` | `--template/-t`, `--no-build`. **No `--overwrite`**, so `ConversionOptions.overwrite` is unreachable from the CLI. |
| API | `docserver/main.py` → `create_document()` | Takes `template`, `build_pdf`, `overwrite` as query params; forwards through `storage.convert_upload()`. |
| Docs | `README.md:234` | Documents `uv run papers convert manuscript.docx --template ieee --overwrite` — a flag that does not exist. |

### The workaround, and what it costs

`scripts/word_to_latex.sh` exists only to move the converter's output somewhere useful.
Each of its steps is a symptom:

1. **It reimplements `snake_case` in shell** to guess the output directory:
   ```sh
   DOC_ID="$(basename "${DOCX}" .docx | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]\+/_/g; s/^_//; s/_$//')"
   ```
   That duplicates `src/docbuilder/utils.py:snake_case`, including its NFKD normalization
   (which the shell version does not actually reproduce — a manuscript with a non-ASCII
   character in the filename already diverges). Any change to `snake_case` breaks the
   script silently: it will `rm -rf` a directory that is not the one the converter writes,
   then fail to find `main.tex`.

2. **It `rm -rf`s the workspace before every run** because the CLI never exposes
   `--overwrite`, and `convert_document` refuses an existing workspace. The script is
   deleting a directory it located by guesswork (see 1).

3. **It strips build artifacts after the fact**:
   ```sh
   rm -f "${DEST}"/main.{aux,bbl,blg,log,out,pdf,toc,synctex.gz}
   ```
   `_copy_template` uses `shutil.copytree`, so on a working checkout — where someone has
   run `scripts/templates/ieee/build.sh` — a stale `main.pdf` and `main.aux` are copied
   into the fresh workspace. A stale `main.pdf` next to freshly converted sources is worse
   than no PDF: it looks like a successful build of the new content. (The script does this
   cleanup twice; the block is duplicated at lines 127–132.)

4. **It copies `references/references.bib` up to `references.bib`.** This one is already
   handled inside the converter (`converter.py:231-232` writes both), so the shell copy is
   dead code kept alive by uncertainty about what the converter guarantees.

5. **It has to invent a collision policy** for `papers/<slug>/latex/`, because the
   converter has no opinion about writing into a directory that holds hand-edited work.

---

## 3. Proposed Changes

### a. `ConversionOptions.output_dir`

```python
@dataclass
class ConversionOptions:
    template: str
    build_pdf: bool = True
    overwrite: bool = False
    output_dir: Path | None = None       # None => DOCUMENTS_ROOT / snake_case(stem)
    layout: Literal["workspace", "flat"] = "workspace"
```

`output_dir=None` preserves today's behavior exactly, so the docserver path and every
existing test are unaffected.

**`layout`** exists because the two destinations want different shapes. `"workspace"` is
what the docserver needs: the stored `.docx`, `manifest.json`, and `<template>/` beneath
the root. `"flat"` is what a paper directory needs: `main.tex`, `sections/`,
`references.bib`, `assets/` directly under `output_dir`, with `manifest.json` alongside
them. A paper directory already has `manuscript/` for the source `.docx`, so `"flat"` does
not re-copy it — the manifest records the absolute source path instead.

Internally, `convert_document` should resolve one pair of paths up front and pass them
down, rather than deriving them mid-function:

```python
root, template_workspace = _resolve_destination(docx_path, options)
```

- workspace layout: `root = output_dir or DOCUMENTS_ROOT / snake_case(stem)`,
  `template_workspace = root / options.template`
- flat layout: `root = template_workspace = output_dir`

Everything downstream (`_build_from_docx`, `_rewrite_main`, `_run_build`) already takes
`workspace` and `template_workspace` as arguments and needs no change. One caveat:
`_run_build` writes `log_path` as `log_file.relative_to(template_workspace.parent)`, which
under the flat layout resolves to a path outside `root`. It should be made relative to
`root` and the workspace layout adjusted to match, or the manifest's `log_path` becomes
wrong for flat conversions.

`output_dir` is resolved (`.expanduser().resolve()`) before use and must not be a file, an
existing non-empty directory outside the collision policy in §3c, or inside the source
`.docx`'s own directory tree in a way that would overwrite the input.

### b. CLI

```
uv run papers convert MANUSCRIPT.docx [--template ieee] [--out DIR] [--flat] [--overwrite] [--no-build]
```

- `--out/-o PATH` — sets `output_dir`. Absolute, or relative to the current directory.
- `--flat/--workspace` — selects `layout`. Default `--flat` **when `--out` is given**
  (the reason to pass `--out` is a paper directory), `--workspace` otherwise. Making the
  default depend on another flag is a small wart; the alternative — always defaulting to
  workspace — means every real invocation types both flags.
- `--overwrite` — the flag `README.md:234` already advertises. It maps straight to
  `ConversionOptions.overwrite`; nothing else needs to change to make it work. Add it
  regardless of whether the rest of this spec lands, since the documentation is currently
  wrong.

The success message must report the real destination rather than the hardcoded
`f"Created workspace: documents/{manifest.document_id}"` it prints today.

Convenience worth adding, since it is the whole point: `--paper <slug>` as sugar for
`--out papers/<slug>/latex --flat`, which also picks the newest `.docx` in
`papers/<slug>/manuscript/` when the positional argument is omitted. That is the last
piece of `word_to_latex.sh` with any real logic in it.

### c. Collision policy for an existing `papers/<slug>/latex/`

The shell script's current answer is: default to writing a sibling `latex.imported/`, and
under `--force` move the existing directory to `latex.bak-<timestamp>/`. Both behaviors
should go.

**Proposed policy: refuse by default, replace under `--overwrite`, never back up and never
merge.**

- **Refuse** when `output_dir` exists and is non-empty. The error names the directory and
  says to pass `--overwrite`. This is the same rule `convert_document` already applies to
  `DOCUMENTS_ROOT` workspaces, so there is one rule to learn rather than two.
- **Replace** under `--overwrite`: delete `output_dir` and write fresh.
- **No timestamped backup.** `papers/` is version controlled. `latex.bak-20260814-101500/`
  is a worse backup than `git stash` or an uncommitted diff, and it accumulates
  directories that are indistinguishable from real content to every glob in the repo,
  including the build scripts. The converter should instead refuse to overwrite a
  destination with uncommitted changes it cannot see — which it cannot detect — so the
  honest version is: refuse unless told, and let git be the safety net. The CLI should say
  so in the `--overwrite` help text.
- **No merge.** Merging generated LaTeX into hand-edited LaTeX is a diff problem, not a
  converter problem. The user who wants it runs the conversion into a scratch directory
  (`--out /tmp/whatever`) and diffs. `latex.imported/` was an attempt to make the converter
  do this automatically, and it produced a directory that no build script knows about and
  that nothing ever deletes.

The APIP paper is the case that motivated `latex.imported/`: `papers/apip/latex/` holds ten
hand-refined section files that a fresh conversion would flatten. Under this policy the
converter refuses to touch them unless the user types `--overwrite`, which is the correct
outcome — and the diff-and-merge workflow the script's help text describes is still
available, just with an explicit `--out`.

### d. `_copy_template` skips build artifacts

Fix this at the source rather than after the copy:

```python
_ARTIFACT_SUFFIXES = {".aux", ".bbl", ".blg", ".log", ".out", ".toc", ".pdf",
                      ".synctex.gz", ".fls", ".fdb_latexmk", ".nav", ".snm", ".vrb"}

def _copy_template(template_dir: Path, destination: Path) -> None:
    shutil.copytree(template_dir, destination, ignore=_ignore_build_artifacts)
    ...
```

Two details worth getting right:

- `.pdf` cannot be blanket-ignored: some templates legitimately vendor figure PDFs. Scope
  the `.pdf` rule to the destination root (the compiled `main.pdf`), or to files whose stem
  matches a `.tex` file in the same directory, and leave `assets/`/`figures/` alone.
- `.synctex.gz` has a two-part suffix; match on the filename, not `Path.suffix`.

This is a correctness fix independent of output targeting — a stale `main.pdf` copied into
a workspace is already a bug for docserver users today, since the API serves
`manifest.build.pdf_path` and the manifest's `build` block is only written when a build
actually ran.

### e. The HTTP API does not get an output directory

`create_document()` keeps exactly the parameters it has today. `storage.convert_upload()`
keeps constructing `ConversionOptions` without `output_dir`, so every API-initiated
conversion lands under `DOCUMENTS_ROOT`.

This is a security boundary, not a scoping decision. `DOCUMENTS_ROOT` is the anchor for the
server's entire path-traversal defense:

- `validate_document_id` (`config.py:24`) allowlists `[A-Za-z0-9_-]+` precisely because
  every id is joined directly to `DOCUMENTS_ROOT` in a dozen places in
  `docserver/main.py` (`:151`, `:198`, `:215`, `:229`, `:246`, `:255`).
- The catch-all route at `docserver/main.py:261-277` turns dot-segment-collapsed requests
  into an explicit 400 instead of a masked 404.

Both defenses assume the same thing: every path the server touches is
`DOCUMENTS_ROOT / <validated-id> / ...`. A caller-supplied output path breaks that
assumption at the root. Even a validated, allowlisted output path would mean the server
writes outside its scratch directory and that `list_documents()`, `delete_document()`, and
the ZIP export operate on trees they no longer own.

Concretely, `output_dir` must be reachable **only** from `docbuilder.cli` and direct
library callers. The rules:

1. No `output_dir` (or `layout`) query parameter, form field, or header on any endpoint.
2. `storage.convert_upload()` never accepts or forwards an output directory. It is the one
   chokepoint between HTTP input and the converter, and it should stay that way.
3. A test asserts the negative — see §5.

If a future feature genuinely needs server-side writes into `papers/`, it should be a
separate, explicitly-rooted API with its own slug allowlist (`papers/<validated-slug>/latex`),
not a general output path.

### f. `scripts/word_to_latex.sh`

Delete it. Every job it does is absorbed:

| Script does | Replaced by |
|---|---|
| Re-derives document id in shell | Not needed — the converter is told the destination |
| `rm -rf documents/<id>` | `--overwrite` |
| `cp -r` result into the paper | `--out` / `--paper` |
| Strips `main.aux`, `main.pdf`, … | §3d, at the copy |
| Copies `references/references.bib` up | Already done in `converter.py:231-232` |
| Picks the newest `.docx` in `manuscript/` | `--paper <slug>` with no positional arg |
| Defaults to `latex.imported/`, backs up to `latex.bak-*/` | §3c — refuse, or `--overwrite` |

If a shell entry point is still wanted for discoverability, it collapses to a one-line
wrapper under `scripts/papers/<slug>/` calling
`uv run papers convert --paper <slug> --no-build`. Prefer the wrapper over the standalone
script so it lives next to the paper's `build.sh` like everything else in the reorg.

`scripts/new-paper.sh` should not gain a conversion step; scaffolding and importing are
separate actions.

---

## 4. Files Affected (implementation reference)

| File | Change |
|------|--------|
| `src/docbuilder/converter.py` | `ConversionOptions.output_dir` + `layout`; `_resolve_destination()`; collision policy; artifact-aware `_copy_template`; `log_path` relative to `root` |
| `src/docbuilder/cli.py` | `--out`, `--flat/--workspace`, `--overwrite`, `--paper`; report the real destination |
| `src/docserver/storage.py` | none (explicitly: `convert_upload` keeps its signature) |
| `src/docserver/main.py` | none |
| `README.md` | CLI section: document `--out`/`--paper`; `--overwrite` becomes true |
| `papers/README.md` | add the import command to the per-paper workflow |
| `scripts/word_to_latex.sh` | deleted |
| `tests/test_converter.py` | output-targeting, collision, artifact-filtering cases |
| `tests/test_workspace.py` | API-cannot-escape assertion |

---

## 5. Verification Plan

- **Unit:** `ConversionOptions()` with no `output_dir` writes to
  `DOCUMENTS_ROOT / snake_case(stem)` exactly as before (regression guard for the
  docserver path). With `output_dir=tmp_path, layout="flat"`, `main.tex`, `sections/*.tex`,
  and `references.bib` land directly under `tmp_path` and nothing is written under
  `DOCUMENTS_ROOT`.
- **Unit:** a template directory seeded with `main.aux`, `main.pdf`, and `main.log` is
  copied without them, while `assets/figure.pdf` survives.
- **CLI:** `papers convert fixture.docx --out <tmp> --flat --no-build` exits 0 and prints
  `<tmp>`; re-running without `--overwrite` exits 1 with an error naming the directory;
  re-running with `--overwrite` succeeds.
- **API-cannot-escape:** `POST /documents` with `output_dir=/etc`, `output_dir=../..`, and
  a form field of the same name is accepted-and-ignored or rejected — never honored — and
  the resulting workspace resolves under `DOCUMENTS_ROOT`. Assert structurally too:
  `inspect.signature(convert_upload)` has no output-path parameter, so the test fails if
  someone later plumbs one through.
- **E2E:** on a checkout where `scripts/templates/ieee/build.sh` has already been run (so
  `templates/latex/ieee/` holds artifacts), run
  `papers convert --paper apip --out <tmp>/latex --flat --no-build`, then
  `bash scripts/papers/apip/build.sh` against that directory; confirm the PDF builds and
  that no `main.pdf` predating the build was ever present.
- **Edge — idempotent re-conversion:** run the same conversion twice into the same
  `--out` with `--overwrite`; the second run leaves a byte-identical tree apart from
  `manifest.json` timestamps. No `latex.bak-*` or `latex.imported` directory appears
  anywhere.
- **Edge:** `--out` pointing at an existing file, at a non-empty directory without
  `--overwrite`, and at a path containing `..` — each fails with a clear message and
  writes nothing.
- **Edge:** a manuscript whose filename contains non-ASCII characters converts correctly
  with `--out` (the case where the old shell `snake_case` diverged from the Python one).

---

## 6. Non-Goals

- Server-side writes into `papers/`. The API stays anchored to `DOCUMENTS_ROOT` (§3e).
- Merging a fresh conversion into hand-edited LaTeX, or any three-way diff support.
  `--out` to a scratch directory plus `diff -r` is the workflow.
- Round-tripping edits in `papers/<slug>/latex/` back into the `.docx`.
- Converting a paper's manuscript from the web UI into that paper's directory.
- Reorganizing what the converter emits (section splitting, figure handling, bibliography
  extraction) — only where it emits.
