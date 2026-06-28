# Critique & Spec 5

## Criticism

**Section detection keys entirely off the literal English style name prefix `"Heading"`, so any manuscript whose headings use a non-English Word locale, a custom/renamed style, the built-in `Title` style, or direct bold formatting is parsed as one giant body blob with no sections — silently destroying the document structure the whole Word→LaTeX conversion exists to produce.**

The converter decides what's a heading with a single string test (`converter.py:160-173`):

```python
style_name = paragraph.style.name if paragraph.style else ""
...
if style_name.startswith("Heading"):
    ...
    level = _heading_level(style_name)
```

and `_heading_level` only understands the `"Heading N"` shape (`converter.py:233-240`). Everything that isn't a paragraph whose style name begins with the exact ASCII word `Heading` falls through to the body-text branch (`converter.py:205-207`). This is fragile in all the ordinary ways real `.docx` files vary:

| Manuscript reality | Style name seen | Detected as heading? |
|--------------------|-----------------|----------------------|
| Word in German / French / Spanish UI | `Überschrift 1`, `Titre 1`, `Título 1` | ❌ no — becomes body text |
| Author used the built-in document **Title** style | `Title` | ❌ no |
| Template with renamed styles (`Section Head`, `H1`) | `Section Head` | ❌ no |
| Headings made by **bold + larger font**, no paragraph style | `Normal` | ❌ no |
| `Heading1` (no space, some exporters) | `Heading1` | ✅ prefix matches, but `_heading_level` may mis-level it |

When detection fails, there is no error and no warning: `ensure_section` emits a single default section and every paragraph — title, headings, body — is concatenated into it as running text (`converter.py:142-152, 205-207`). The output `.tex` compiles, but it's a wall of text with no `\section` structure, which for a conference paper tool is a total conversion failure dressed up as success. The user only discovers it by reading the rendered PDF.

The brittleness is sharpest for exactly the inputs a research tool should expect: manuscripts written in non-English Word installations, and documents that use Word's *Title* style for the paper title (extremely common) — both of which this code cannot see as structure.

---

## Spec

### Goal

Recognize headings robustly across locales, custom styles, and direct formatting, and never silently produce a structureless document — if structure can't be found, say so.

### Approach

Detect headings by *outline level* rather than English style-name text. Word stores a paragraph's outline level (`w:outlineLvl`) independently of the (localizable) style display name; built-in heading styles and the Title style map to known `style_id`s (`Heading1`, `Title`) that are stable across locales even when the *display* name is translated. Use those signals, fall back to formatting heuristics, and emit a diagnostic when no headings are found.

### Specific Changes

**1. `converter.py` — detect by style_id and outline level, not display name.** Read `paragraph.style.style_id` (stable: `Heading1`…`Heading9`, `Title`) and the paragraph's `w:outlineLvl` (via the underlying XML) to assign a level. This handles localized display names (`Überschrift 1` still has `style_id="Heading1"`).

**2. `converter.py` — map `Title` to the document title / level-1.** Treat the `Title` style as the paper title (or a top-level section) instead of body text.

**3. `converter.py` — formatting fallback.** When no styled headings are found at all, apply a conservative heuristic (short paragraph, bold, larger font, no terminal period) to nominate headings, behind a flag so it can't misfire on papers that *do* use styles.

**4. `converter.py` — diagnostic, not silent failure.** If the finished parse yields zero sections (or one section containing the entire body), record a warning in the manifest (e.g. `structure_warning: "no headings detected; output is unsectioned"`) and surface it in the API/UI so the user knows the conversion lost structure rather than discovering it in the PDF.

### Acceptance Criteria

1. A `.docx` whose headings use the German `Überschrift 1` style (style_id `Heading1`) produces the same sectioned LaTeX as the English `Heading 1` equivalent.
2. A document using the `Title` style for its title yields a title/level-1 element, not body text.
3. A document with no styled headings triggers a `structure_warning` in the manifest and the API response, and (with the fallback enabled) nominates plausible headings.
4. Existing English `Heading N` documents convert exactly as before (no regression).
5. New tests cover: localized style_id, `Title` style, and the zero-heading warning path.
