## Criticism

**`_rewrite_main` appends the converted paper's sections after the template's Lorem-ipsum boilerplate instead of replacing it, so the compiled PDF always contains placeholder content before the user's actual paper.**

`converter.py:299–329` (`_rewrite_main`) rewrites `main.tex` by splitting on `\begin{document}` and `\end{document}`, then **appending** the user's generated `\input{}` directives after the entire original body:

```python
rebuilt = (
    before
    + "\\begin{document}\n"
    + body                    # ← full original template body kept intact
    + "\n"
    + "".join(section_inputs) # ← user sections appended at the end
    + "% ---- End auto-generated sections ----\n"
    + "\\end{document}\n"
    + tail
)
```

The IEEE `main.tex` body contains (in order): the placeholder title block ("Paper Title Goes Here", "First Author"), five `\input{sections/...}` calls pointing to Lorem-ipsum `.tex` files, and `\bibliography{references}`. `_copy_template` (`converter.py:111–113`) copies those Lorem-ipsum section files into the workspace before conversion, so they are present and LaTeX can read them.

The resulting compiled PDF therefore always has this structure:

1. **Title: "Paper Title Goes Here"** — placeholder, never set to the actual manuscript title
2. **Authors: "First Author / Second Author"** — placeholder affiliation block
3. **Section: Introduction** — Lorem ipsum from `sections/introduction.tex`
4. **Section: Related Work** — Lorem ipsum from `sections/related_work.tex`
5. *(three more Lorem-ipsum template sections)*
6. **References** — bibliography call fires here, mid-document, before user content
7. **User's actual paper content** — appended after the bibliography, at the very end

This is universally broken: 100% of conversions produce PDFs in which the user's manuscript is buried after five Lorem-ipsum sections and a misplaced bibliography. The title on the PDF cover page is always wrong. The test suite does not exercise a full round-trip build, so this has gone undetected.

The root cause is that `_rewrite_main` was written to *add* to a document, not to *replace* its content sections. It never clears the original `\input{sections/...}` lines from the template body, nor does it update the title/author macros.

---

## Spec

### Goal

Produce a `main.tex` whose compiled PDF begins with the correct title, contains only the user's converted sections (in order), and places the bibliography after the final section — matching the structure of a properly formatted conference submission.

### Approach

`_rewrite_main` must do three things it currently does not:

**1. Strip existing `\input{sections/...}` and `\input{references/...}` lines from the body.**
After splitting on `\begin{document}` / `\end{document}`, filter every line in `body` that matches `\input{sections/...}` or `\input{references/...}`. This removes the template placeholder section calls so they do not appear in the rebuilt file. Preserve all other body content (title macros, `\maketitle`, `\bibliographystyle`, `\bibliography`, etc.).

**2. Insert the user's section `\input{}` calls immediately before the bibliography command.**
Locate `\bibliographystyle` or `\bibliography` in the cleaned body. Insert the generated `\input{sections/<slug>}` block just before that line so the paper body appears before the references, as expected.  
If neither bibliography command is found (edge case), append the section inputs at the end of the body before `\end{document}`.

**3. Propagate the document title into `\title{...}`.**
The manifest already carries `title` (set from the docx filename stem). Rewrite the `\title{...}` line in `before` (the preamble) with the manifest title so the PDF cover page is not permanently "Paper Title Goes Here".

### Specific changes

| File | Change |
|---|---|
| `src/docbuilder/converter.py:299–329` | Rewrite `_rewrite_main(template_workspace, sections)` to accept a `title: str` parameter. Clean the body of existing `\input{sections/...}` lines. Insert generated section inputs before `\bibliography`/`\bibliographystyle`. Substitute the real title into `\title{...}`. |
| `src/docbuilder/converter.py:218` | Pass `manifest.title` to `_rewrite_main`: `_rewrite_main(template_workspace, manifest.sections, title=manifest.title)`. |
| `src/docbuilder/converter.py:111–113` (`_copy_template`) | After copying, delete the placeholder section files (`sections/*.tex`) from the workspace so they cannot be accidentally `\input`-ted even if a bug reintroduces stale `\input{}` lines. |
| `tests/test_converter.py` *(new)* | Unit tests for `_rewrite_main`: verify that the output contains no Lorem-ipsum `\input{}` calls; that each user section slug appears exactly once; that `\bibliography` comes after all `\input{sections/...}` lines; and that the title macro contains the passed title. Use a minimal synthetic `main.tex` fixture — no LaTeX toolchain required. |

### Acceptance criteria

1. After conversion the workspace `main.tex` contains **no** `\input{sections/abstract}`, `\input{sections/introduction}`, or any other original template section path.
2. Every slug from `manifest.sections` appears exactly once in `main.tex`, in `order` sequence.
3. All `\input{sections/<slug>}` lines appear **before** the `\bibliography{...}` line in the output file.
4. The `\title{...}` macro in `main.tex` contains the document's title, not "Paper Title Goes Here".
5. The placeholder `.tex` files (`sections/abstract.tex`, `sections/introduction.tex`, etc.) are absent from the workspace after conversion, so a stale `\input{}` cannot silently pull in Lorem-ipsum content.
6. Existing tests continue to pass; the new `test_converter.py` covers the four structural invariants above without requiring a LaTeX installation.
