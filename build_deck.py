"""Build the Research Paper Workspace slide deck per POWERPOINT_SPEC.md."""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import pptx.oxml.ns as nsmap
from lxml import etree

# ── Palette ──────────────────────────────────────────────────────────────────
NAVY    = RGBColor(0x1A, 0x23, 0x4E)   # slide background / dark elements
TEAL    = RGBColor(0x00, 0x87, 0x8A)   # accent / headings
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
SILVER  = RGBColor(0xE8, 0xEC, 0xF0)   # light body background
AMBER   = RGBColor(0xF5, 0xA6, 0x23)   # highlight / callout
CHARCOAL= RGBColor(0x2D, 0x2D, 0x2D)   # body text on light slides

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

OUTPUT = "research_paper_workspace.pptx"


# ── Helpers ───────────────────────────────────────────────────────────────────

def new_prs() -> Presentation:
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs: Presentation):
    """Add a truly blank slide (no placeholder boxes)."""
    blank_layout = prs.slide_layouts[6]
    return prs.slides.add_slide(blank_layout)


def fill_solid(shape, color: RGBColor):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def add_rect(slide, left, top, width, height, color: RGBColor):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    fill_solid(shape, color)
    shape.line.fill.background()
    return shape


def add_textbox(slide, left, top, width, height,
                text, font_size=18, bold=False, italic=False,
                color=WHITE, align=PP_ALIGN.LEFT, wrap=True):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txBox


def add_bullet_box(slide, left, top, width, height,
                   title, bullets,
                   title_size=22, bullet_size=17,
                   title_color=TEAL, bullet_color=CHARCOAL,
                   bg_color=None):
    """Titled box with bullet list."""
    if bg_color:
        add_rect(slide, left, top, width, height, bg_color)

    # title
    add_textbox(slide, left + Inches(0.15), top + Inches(0.1),
                width - Inches(0.3), Inches(0.45),
                title, font_size=title_size, bold=True, color=title_color)

    # bullets
    txBox = slide.shapes.add_textbox(
        left + Inches(0.25), top + Inches(0.6),
        width - Inches(0.4), height - Inches(0.7)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    first = True
    for b in bullets:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(4)
        run = p.add_run()
        run.text = f"• {b}"
        run.font.size = Pt(bullet_size)
        run.font.color.rgb = bullet_color
    return txBox


def dark_background(slide):
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, NAVY)


def light_background(slide):
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, SILVER)


def accent_bar(slide, color=TEAL, height=Inches(0.08)):
    add_rect(slide, 0, SLIDE_H - height, SLIDE_W, height, color)


def slide_number(slide, num: int, total=12):
    add_textbox(slide,
                SLIDE_W - Inches(1.2), SLIDE_H - Inches(0.4),
                Inches(1.0), Inches(0.35),
                f"{num} / {total}",
                font_size=11, color=RGBColor(0x88, 0x88, 0x88),
                align=PP_ALIGN.RIGHT)


def placeholder_image(slide, left, top, width, height, label,
                      bg=RGBColor(0x30, 0x40, 0x60)):
    """Grey box standing in for a real screenshot / diagram."""
    add_rect(slide, left, top, width, height, bg)
    add_textbox(slide, left, top + height / 2 - Pt(12),
                width, Inches(0.4),
                f"[ {label} ]",
                font_size=13, italic=True,
                color=RGBColor(0xAA, 0xBB, 0xCC),
                align=PP_ALIGN.CENTER)


# ── Slide builders ────────────────────────────────────────────────────────────

def slide_01_title(prs):
    """Title slide."""
    s = blank_slide(prs)
    dark_background(s)

    # teal left stripe
    add_rect(s, 0, 0, Inches(0.35), SLIDE_H, TEAL)

    # main title
    add_textbox(s, Inches(0.7), Inches(1.5), Inches(9.5), Inches(1.6),
                "Research Paper Workspace",
                font_size=44, bold=True, color=WHITE)

    # subtitle
    add_textbox(s, Inches(0.7), Inches(3.1), Inches(9.5), Inches(0.7),
                "Word → LaTeX  ·  Build  ·  Review  ·  Critique",
                font_size=26, color=TEAL)

    # tagline
    add_textbox(s, Inches(0.7), Inches(4.0), Inches(9.5), Inches(0.55),
                "Upload a .docx — get a conference-ready PDF in minutes.",
                font_size=18, italic=True, color=RGBColor(0xB0, 0xC4, 0xDE))

    # decorative amber line
    add_rect(s, Inches(0.7), Inches(2.95), Inches(5.0), Inches(0.05), AMBER)

    accent_bar(s)
    slide_number(s, 1)


def slide_02_problem(prs):
    """The problem."""
    s = blank_slide(prs)
    light_background(s)

    # header band
    add_rect(s, 0, 0, SLIDE_W, Inches(1.15), NAVY)
    add_textbox(s, Inches(0.5), Inches(0.25), Inches(11), Inches(0.75),
                "The Problem", font_size=32, bold=True, color=WHITE)

    pain_points = [
        "Manually reformatting a Word manuscript into IEEE / NeurIPS / ACM / AAAI LaTeX takes hours.",
        "Copy-paste errors, inconsistent figure refs, and broken BibTeX are the norm.",
        "Authors switch conferences → rebuild the entire LaTeX tree from scratch.",
        "Reviewing AI-generated academic prose ('this paper proposes…') is ad hoc and subjective.",
        "No standard tool connects upload → structured LaTeX → build → critique in one workflow.",
    ]

    for i, pt in enumerate(pain_points):
        top = Inches(1.4) + i * Inches(1.0)
        add_rect(s, Inches(0.4), top, Inches(12.1), Inches(0.82),
                 RGBColor(0xFF, 0xFF, 0xFF))
        # amber bullet bar
        add_rect(s, Inches(0.4), top, Inches(0.08), Inches(0.82), AMBER)
        add_textbox(s, Inches(0.65), top + Inches(0.12),
                    Inches(11.6), Inches(0.65),
                    pt, font_size=16, color=CHARCOAL)

    accent_bar(s)
    slide_number(s, 2)


def slide_03_what_it_is(prs):
    """What it is — overview."""
    s = blank_slide(prs)
    dark_background(s)

    add_textbox(s, Inches(0.5), Inches(0.25), Inches(12), Inches(0.7),
                "What It Is", font_size=32, bold=True, color=TEAL)
    add_rect(s, Inches(0.5), Inches(0.92), Inches(5.5), Inches(0.04), AMBER)

    # flow boxes
    steps = [
        ("Upload .docx", "python-docx parses headings,\nbody, figures, references"),
        ("Per-section LaTeX", "sections/intro.tex\nsections/related.tex …"),
        ("Conference PDF", "IEEE · NeurIPS · ACM · AAAI\nbuild.sh pipeline"),
        ("Edit & Recompile", "Section editor → Recompile\nbuild-log surfaced in UI"),
        ("Critique", "AI-genericness score\nde-AI tips per section"),
    ]

    box_w = Inches(2.35)
    box_h = Inches(2.8)
    gap   = Inches(0.12)
    start_x = Inches(0.3)
    top   = Inches(1.2)

    for i, (title, desc) in enumerate(steps):
        x = start_x + i * (box_w + gap)
        add_rect(s, x, top, box_w, box_h, RGBColor(0x25, 0x32, 0x65))
        add_rect(s, x, top, box_w, Inches(0.45), TEAL)
        add_textbox(s, x + Inches(0.1), top + Inches(0.07),
                    box_w - Inches(0.2), Inches(0.35),
                    title, font_size=14, bold=True, color=WHITE)
        add_textbox(s, x + Inches(0.12), top + Inches(0.55),
                    box_w - Inches(0.25), Inches(2.1),
                    desc, font_size=13, color=RGBColor(0xB0, 0xC8, 0xE8))
        # arrow (skip after last)
        if i < len(steps) - 1:
            ax = x + box_w + Inches(0.01)
            ay = top + box_h / 2 - Inches(0.12)
            add_textbox(s, ax, ay, gap + Inches(0.08), Inches(0.3),
                        "▶", font_size=14, color=TEAL, align=PP_ALIGN.CENTER)

    # interfaces row
    add_textbox(s, Inches(0.5), Inches(4.25), Inches(12), Inches(0.45),
                "Interfaces:", font_size=17, bold=True, color=AMBER)
    ifaces = ["Web UI (React/Vite)", "REST API (FastAPI)", "CLI (Typer)"]
    for j, iface in enumerate(ifaces):
        bx = Inches(0.5) + j * Inches(4.1)
        add_rect(s, bx, Inches(4.75), Inches(3.9), Inches(0.65),
                 RGBColor(0x25, 0x32, 0x65))
        add_textbox(s, bx + Inches(0.15), Inches(4.85),
                    Inches(3.6), Inches(0.5),
                    iface, font_size=16, color=WHITE)

    accent_bar(s)
    slide_number(s, 3)


def slide_04_architecture(prs):
    """Architecture overview."""
    s = blank_slide(prs)
    light_background(s)

    add_rect(s, 0, 0, SLIDE_W, Inches(1.1), NAVY)
    add_textbox(s, Inches(0.5), Inches(0.22), Inches(10), Inches(0.7),
                "Architecture", font_size=32, bold=True, color=WHITE)

    # Four component boxes
    components = [
        ("docbuilder", "converter · CLI · sandbox\ntemplate registry · sections writer",
         RGBColor(0x00, 0x60, 0x64)),
        ("docserver\n(FastAPI)", "REST API · auth · CORS\ndocuments/<id>/ workspaces",
         RGBColor(0x1A, 0x50, 0x8B)),
        ("critic", "per-section criticisms\nAI-genericness score\npluggable providers",
         RGBColor(0x6B, 0x21, 0x6B)),
        ("web\n(React/Vite)", "upload · PDF tab · LaTeX editor\nCritic gauges · template dropdown",
         RGBColor(0x7A, 0x3A, 0x00)),
    ]

    box_w = Inches(2.95)
    box_h = Inches(3.4)
    top   = Inches(1.3)
    for i, (name, desc, color) in enumerate(components):
        x = Inches(0.3) + i * (box_w + Inches(0.1))
        add_rect(s, x, top, box_w, box_h, color)
        # white name tag
        add_rect(s, x, top, box_w, Inches(0.55), RGBColor(0xFF, 0xFF, 0xFF))
        add_textbox(s, x + Inches(0.1), top + Inches(0.07),
                    box_w - Inches(0.2), Inches(0.45),
                    name, font_size=16, bold=True, color=color)
        add_textbox(s, x + Inches(0.15), top + Inches(0.65),
                    box_w - Inches(0.3), Inches(2.5),
                    desc, font_size=14, color=WHITE)

    # Workspace note
    add_rect(s, Inches(0.3), Inches(4.85), Inches(12.4), Inches(0.7),
             RGBColor(0x30, 0x30, 0x30))
    add_textbox(s, Inches(0.5), Inches(4.92), Inches(12), Inches(0.5),
                "documents/<id>/   —   per-upload workspace: main.tex · sections/*.tex · references.bib · build-log · manifest.json",
                font_size=13, color=RGBColor(0xCC, 0xCC, 0xCC))

    accent_bar(s)
    slide_number(s, 4)


def slide_05_conversion_pipeline(prs):
    """Conversion pipeline."""
    s = blank_slide(prs)
    dark_background(s)

    add_textbox(s, Inches(0.5), Inches(0.2), Inches(12), Inches(0.7),
                "Conversion Pipeline", font_size=32, bold=True, color=TEAL)
    add_rect(s, Inches(0.5), Inches(0.88), Inches(6.0), Inches(0.04), AMBER)

    pipeline = [
        ("1. Parse", ".docx\n(python-docx)"),
        ("2. Split", "headings →\nsections/*.tex"),
        ("3. Extract", "figures, captions\nBibTeX references"),
        ("4. Assemble", "main.tex with\n\\input{} directives"),
        ("5. Build", "per-conference\nbuild.sh"),
        ("6. Output", "PDF + LaTeX\n.zip export"),
    ]

    bw = Inches(1.95)
    bh = Inches(2.2)
    gap = Inches(0.09)
    sx = Inches(0.3)
    ty = Inches(1.1)

    for i, (step, desc) in enumerate(pipeline):
        x = sx + i * (bw + gap)
        bg = TEAL if i % 2 == 0 else RGBColor(0x00, 0x60, 0x6B)
        add_rect(s, x, ty, bw, bh, bg)
        add_textbox(s, x + Inches(0.1), ty + Inches(0.12),
                    bw - Inches(0.2), Inches(0.45),
                    step, font_size=15, bold=True, color=WHITE)
        add_textbox(s, x + Inches(0.12), ty + Inches(0.65),
                    bw - Inches(0.25), Inches(1.4),
                    desc, font_size=13, color=RGBColor(0xD8, 0xF4, 0xF4))
        if i < len(pipeline) - 1:
            ax = x + bw + Inches(0.0)
            add_textbox(s, ax, ty + bh / 2 - Inches(0.2),
                        gap + Inches(0.06), Inches(0.4),
                        "▶", font_size=13, color=AMBER, align=PP_ALIGN.CENTER)

    # sandbox callout
    add_rect(s, Inches(0.3), Inches(3.55), Inches(12.4), Inches(1.0),
             RGBColor(0x25, 0x32, 0x65))
    add_rect(s, Inches(0.3), Inches(3.55), Inches(0.12), Inches(1.0), AMBER)
    add_textbox(s, Inches(0.55), Inches(3.65), Inches(11.8), Inches(0.8),
                "Build step runs inside the sandbox (src/docbuilder/sandbox.py): no shell-escape, "
                "restricted file IO, rlimits, timeout.  Set LATEX_SANDBOX=docker for container isolation.",
                font_size=14, color=RGBColor(0xB0, 0xC8, 0xE8))

    # reference extraction note
    add_rect(s, Inches(0.3), Inches(4.75), Inches(12.4), Inches(0.9),
             RGBColor(0x20, 0x28, 0x50))
    add_textbox(s, Inches(0.5), Inches(4.85), Inches(12.0), Inches(0.7),
                "References: Word's built-in Citations XML first → heuristic paragraph extraction fallback → "
                "valid BibTeX stubs so pdflatex never aborts.  Warnings surfaced in the UI.",
                font_size=13, italic=True, color=RGBColor(0x99, 0xAA, 0xCC))

    accent_bar(s)
    slide_number(s, 5)


def slide_06_template_selection(prs):
    """Dynamic template selection."""
    s = blank_slide(prs)
    light_background(s)

    add_rect(s, 0, 0, SLIDE_W, Inches(1.1), NAVY)
    add_textbox(s, Inches(0.5), Inches(0.22), Inches(12), Inches(0.7),
                "Dynamic Template Selection", font_size=32, bold=True, color=WHITE)

    # Left: how it works
    add_bullet_box(
        s, Inches(0.3), Inches(1.25), Inches(6.0), Inches(5.5),
        "How it works",
        [
            "Backend registry scans latex/*/ at startup",
            "Each folder with a build.sh becomes a template",
            "GET /templates returns the live list",
            "UI dropdown is driven by that API response",
            "Adding a new folder → it appears automatically",
            "No code changes required",
        ],
        title_color=TEAL, bullet_color=CHARCOAL,
        bg_color=WHITE,
    )

    # Right: current templates
    templates = [
        ("IEEE", "ieee/build.sh", "Two-column · 10 pt · Times"),
        ("NeurIPS", "neurips/build.sh", "Style auto-downloaded yearly"),
        ("ACM", "acm/build.sh", "acmart.cls version-controlled"),
        ("AAAI", "aaai/build.sh", "Aux files cleaned before build"),
    ]
    bw = Inches(5.8)
    bh = Inches(5.5)
    bx = Inches(6.8)
    add_rect(s, bx, Inches(1.25), bw, bh, WHITE)
    add_textbox(s, bx + Inches(0.15), Inches(1.35), bw, Inches(0.45),
                "Current templates", font_size=20, bold=True, color=TEAL)

    for i, (name, script, note) in enumerate(templates):
        ty = Inches(1.95) + i * Inches(1.15)
        add_rect(s, bx + Inches(0.15), ty, bw - Inches(0.3), Inches(0.95),
                 RGBColor(0xF0, 0xF4, 0xF8))
        add_rect(s, bx + Inches(0.15), ty, Inches(0.08), Inches(0.95), TEAL)
        add_textbox(s, bx + Inches(0.35), ty + Inches(0.08),
                    Inches(1.1), Inches(0.4),
                    name, font_size=16, bold=True, color=NAVY)
        add_textbox(s, bx + Inches(1.55), ty + Inches(0.08),
                    Inches(3.8), Inches(0.4),
                    script, font_size=13, italic=True, color=TEAL)
        add_textbox(s, bx + Inches(0.35), ty + Inches(0.52),
                    bw - Inches(0.6), Inches(0.35),
                    note, font_size=12, color=CHARCOAL)

    accent_bar(s)
    slide_number(s, 6)


def slide_07_edit_recompile(prs):
    """Edit / Recompile / Export."""
    s = blank_slide(prs)
    dark_background(s)

    add_textbox(s, Inches(0.5), Inches(0.2), Inches(12), Inches(0.7),
                "Edit · Recompile · Export", font_size=32, bold=True, color=TEAL)
    add_rect(s, Inches(0.5), Inches(0.88), Inches(5.5), Inches(0.04), AMBER)

    features = [
        ("Section editor",
         "Each sections/*.tex file is editable directly in the browser. "
         "Changes are saved server-side into the document workspace."),
        ("Recompile",
         "POST /documents/{id}/build triggers the full pdflatex → bibtex → pdflatex×2 "
         "pipeline; the refreshed PDF is streamed back to the viewer."),
        ("Build-log surfacing",
         "Raw LaTeX stderr is stored in the workspace and exposed via GET /documents/{id}/log. "
         "Errors are highlighted in the UI — no terminal needed."),
        ("LaTeX .zip export",
         "GET /documents/{id}/export bundles main.tex, all sections/*.tex, references.bib, "
         "and figures into a self-contained archive for offline editing."),
    ]

    for i, (title, desc) in enumerate(features):
        row = i // 2
        col = i % 2
        bx = Inches(0.3) + col * Inches(6.55)
        ty = Inches(1.1) + row * Inches(2.75)
        bw = Inches(6.2)
        bh = Inches(2.55)
        add_rect(s, bx, ty, bw, bh, RGBColor(0x1E, 0x2A, 0x5A))
        add_rect(s, bx, ty, bw, Inches(0.48), TEAL)
        add_textbox(s, bx + Inches(0.12), ty + Inches(0.08),
                    bw - Inches(0.25), Inches(0.38),
                    title, font_size=16, bold=True, color=WHITE)
        add_textbox(s, bx + Inches(0.15), ty + Inches(0.6),
                    bw - Inches(0.3), Inches(1.8),
                    desc, font_size=13, color=RGBColor(0xB8, 0xCC, 0xE8))

    accent_bar(s)
    slide_number(s, 7)


def slide_08_critic(prs):
    """The Critic."""
    s = blank_slide(prs)
    light_background(s)

    add_rect(s, 0, 0, SLIDE_W, Inches(1.1), NAVY)
    add_textbox(s, Inches(0.5), Inches(0.22), Inches(12), Inches(0.7),
                "The Critic", font_size=32, bold=True, color=WHITE)

    # Left column
    add_bullet_box(
        s, Inches(0.3), Inches(1.25), Inches(5.9), Inches(5.4),
        "Per-section output",
        [
            "3 targeted criticisms per section",
            "AI-genericness score (0–100)",
            "Hybrid: heuristics + LLM scoring",
            "De-AI rewrite tips",
            "Gauge widget in the UI",
        ],
        title_color=TEAL, bullet_color=CHARCOAL, bg_color=WHITE,
        title_size=20, bullet_size=16,
    )

    # Right column — providers
    add_rect(s, Inches(6.5), Inches(1.25), Inches(6.5), Inches(5.4), WHITE)
    add_textbox(s, Inches(6.65), Inches(1.35), Inches(6.2), Inches(0.45),
                "Pluggable providers", font_size=20, bold=True, color=TEAL)

    providers = [
        ("stub",      "Always returns fixtures — zero cost, works offline"),
        ("claude",    "Anthropic Claude API — highest quality scoring"),
        ("ollama",    "Local Ollama models — private, no egress"),
        ("cerebras",  "Cerebras gpt-oss-120b — fast inference"),
    ]
    for i, (name, desc) in enumerate(providers):
        ty = Inches(1.95) + i * Inches(1.1)
        bx = Inches(6.65)
        bw = Inches(6.1)
        add_rect(s, bx, ty, bw, Inches(0.92), RGBColor(0xF0, 0xF4, 0xF8))
        add_rect(s, bx, ty, Inches(0.08), Inches(0.92), AMBER)
        add_textbox(s, bx + Inches(0.2), ty + Inches(0.08),
                    Inches(1.1), Inches(0.38),
                    name, font_size=15, bold=True, color=NAVY)
        add_textbox(s, bx + Inches(1.4), ty + Inches(0.08),
                    Inches(4.5), Inches(0.38),
                    desc, font_size=13, color=CHARCOAL)

    # ad-hoc note
    add_rect(s, Inches(0.3), Inches(6.8), Inches(12.7), Inches(0.5),
             RGBColor(0xE8, 0xF0, 0xFF))
    add_textbox(s, Inches(0.5), Inches(6.85), Inches(12.0), Inches(0.38),
                "Ad-hoc mode: upload any PDF or DOCX directly to the Critic endpoint — "
                "no conversion step required.",
                font_size=13, italic=True, color=CHARCOAL)

    accent_bar(s)
    slide_number(s, 8)


def slide_09_security(prs):
    """Security."""
    s = blank_slide(prs)
    dark_background(s)

    add_textbox(s, Inches(0.5), Inches(0.2), Inches(12), Inches(0.7),
                "Security", font_size=32, bold=True, color=TEAL)
    add_rect(s, Inches(0.5), Inches(0.88), Inches(3.5), Inches(0.04), AMBER)

    security_items = [
        ("Sandboxed LaTeX build",
         [
             "src/docbuilder/sandbox.py",
             "No shell-escape (\\write18 disabled)",
             "Restricted file I/O (openin_any / openout_any = p)",
             "rlimits: CPU, memory, file-size caps",
             "Hard timeout per build job",
             "LATEX_SANDBOX=docker for full container isolation",
         ]),
        ("API authentication",
         [
             "Bearer token required when DOCSERVER_API_KEY is set",
             "src/docserver/auth.py",
             "Returns 401 on missing / invalid key",
             "Key passed via Authorization header",
         ]),
        ("CORS hardening",
         [
             "Allowed origins set via DOCSERVER_CORS_ORIGINS",
             "Defaults to localhost only in dev mode",
             "FastAPI CORSMiddleware with explicit origin list",
         ]),
    ]

    col_w = Inches(4.1)
    for col, (title, bullets) in enumerate(security_items):
        cx = Inches(0.3) + col * (col_w + Inches(0.12))
        add_rect(s, cx, Inches(1.1), col_w, Inches(5.4),
                 RGBColor(0x1A, 0x28, 0x55))
        add_rect(s, cx, Inches(1.1), col_w, Inches(0.5), TEAL)
        add_textbox(s, cx + Inches(0.12), Inches(1.17),
                    col_w - Inches(0.25), Inches(0.4),
                    title, font_size=15, bold=True, color=WHITE)
        for i, b in enumerate(bullets):
            ty = Inches(1.75) + i * Inches(0.72)
            add_rect(s, cx + Inches(0.15), ty, Inches(0.06), Inches(0.45), AMBER)
            add_textbox(s, cx + Inches(0.32), ty + Inches(0.02),
                        col_w - Inches(0.5), Inches(0.55),
                        b, font_size=12, color=RGBColor(0xCC, 0xDD, 0xF0))

    accent_bar(s)
    slide_number(s, 9)


def slide_10_deployment(prs):
    """Deployment."""
    s = blank_slide(prs)
    light_background(s)

    add_rect(s, 0, 0, SLIDE_W, Inches(1.1), NAVY)
    add_textbox(s, Inches(0.5), Inches(0.22), Inches(12), Inches(0.7),
                "Deployment", font_size=32, bold=True, color=WHITE)

    # CI/CD flow
    flow_items = [
        ("git push", "trigger"),
        ("GitHub\nActions", "CI/CD"),
        ("Docker\nbuild", "image"),
        ("ECR\npush", "registry"),
        ("ECS Express\ndeploy", "live"),
    ]

    bw = Inches(2.2)
    bh = Inches(1.6)
    ty = Inches(1.3)
    for i, (label, sublabel) in enumerate(flow_items):
        bx = Inches(0.3) + i * (bw + Inches(0.17))
        color = TEAL if i % 2 == 0 else NAVY
        add_rect(s, bx, ty, bw, bh, color)
        add_textbox(s, bx + Inches(0.1), ty + Inches(0.2),
                    bw - Inches(0.2), Inches(0.7),
                    label, font_size=15, bold=True, color=WHITE,
                    align=PP_ALIGN.CENTER)
        add_textbox(s, bx + Inches(0.1), ty + Inches(0.95),
                    bw - Inches(0.2), Inches(0.4),
                    sublabel, font_size=11, italic=True,
                    color=RGBColor(0xAA, 0xCC, 0xFF),
                    align=PP_ALIGN.CENTER)
        if i < len(flow_items) - 1:
            ax = bx + bw + Inches(0.01)
            add_textbox(s, ax, ty + bh / 2 - Inches(0.15),
                        Inches(0.2), Inches(0.3),
                        "▶", font_size=14, color=NAVY, align=PP_ALIGN.CENTER)

    # Details
    details = [
        ("Dockerfiles",
         "docker/Dockerfile.backend · docker/Dockerfile.frontend\n"
         "Multi-stage builds; frontend assets baked into Nginx image."),
        ("GitHub Actions",
         ".github/workflows/deploy-aws.yml\n"
         "OIDC auth (no long-lived AWS keys); builds on push to main."),
        ("AWS ECS Express Mode",
         "See DEPLOY-AWS.md for full setup.\n"
         "ECS service + ALB; ECR as the image registry."),
    ]

    for i, (title, desc) in enumerate(details):
        bx = Inches(0.3) + i * Inches(4.35)
        ty2 = Inches(3.15)
        add_rect(s, bx, ty2, Inches(4.1), Inches(3.2), WHITE)
        add_rect(s, bx, ty2, Inches(4.1), Inches(0.45), NAVY)
        add_textbox(s, bx + Inches(0.12), ty2 + Inches(0.07),
                    Inches(3.8), Inches(0.35),
                    title, font_size=14, bold=True, color=WHITE)
        add_textbox(s, bx + Inches(0.15), ty2 + Inches(0.55),
                    Inches(3.8), Inches(2.5),
                    desc, font_size=13, color=CHARCOAL)

    accent_bar(s)
    slide_number(s, 10)


def slide_11_demo(prs):
    """Demo — screenshots."""
    s = blank_slide(prs)
    dark_background(s)

    add_textbox(s, Inches(0.5), Inches(0.18), Inches(12), Inches(0.65),
                "Demo Walkthrough", font_size=32, bold=True, color=TEAL)
    add_rect(s, Inches(0.5), Inches(0.82), Inches(4.5), Inches(0.04), AMBER)

    screenshots = [
        ("Upload .docx", Inches(0.3),  Inches(0.95)),
        ("PDF viewer",   Inches(3.6),  Inches(0.95)),
        ("LaTeX editor", Inches(6.85), Inches(0.95)),
        ("Critic gauges",Inches(10.1), Inches(0.95)),
    ]

    sw = Inches(3.1)
    sh = Inches(5.8)
    for label, lx, ly in screenshots:
        placeholder_image(s, lx, ly + Inches(0.1), sw, sh - Inches(0.5), label)
        add_textbox(s, lx, ly + sh - Inches(0.35), sw, Inches(0.38),
                    label, font_size=12, bold=True, color=AMBER,
                    align=PP_ALIGN.CENTER)

    accent_bar(s)
    slide_number(s, 11)


def slide_12_roadmap(prs):
    """Roadmap / closing."""
    s = blank_slide(prs)
    light_background(s)

    add_rect(s, 0, 0, SLIDE_W, Inches(1.1), NAVY)
    add_textbox(s, Inches(0.5), Inches(0.22), Inches(12), Inches(0.7),
                "Roadmap & Closing", font_size=32, bold=True, color=WHITE)

    # Left: roadmap
    add_bullet_box(
        s, Inches(0.3), Inches(1.25), Inches(6.2), Inches(5.0),
        "Roadmap",
        [
            "Reference extraction: richer BibTeX parsing from Word XML",
            "More conference templates (CVPR, EMNLP, VLDB …)",
            "Diff view: compare original .docx to generated LaTeX",
            "Multi-document workspaces / project folders",
            "Live collaborative editing via WebSockets",
            "slides2video integration: deck → narrated MP4",
        ],
        title_color=TEAL, bullet_color=CHARCOAL, bg_color=WHITE,
        title_size=20, bullet_size=15,
    )

    # Right: links / closing
    add_rect(s, Inches(6.8), Inches(1.25), Inches(6.2), Inches(5.0),
             RGBColor(0x1A, 0x23, 0x4E))

    add_textbox(s, Inches(6.95), Inches(1.4), Inches(5.8), Inches(0.45),
                "Resources", font_size=20, bold=True, color=TEAL)

    links = [
        ("MANUAL.md", "Full user guide + API reference"),
        ("README.md", "Quick-start & architecture overview"),
        ("DEPLOY-AWS.md", "ECS Express deployment guide"),
        ("CRITIQUE_SPEC.md", "Critic design & scoring algorithm"),
        ("research/apip_sim/", "APIP simulation (port 8100)"),
    ]

    for i, (name, desc) in enumerate(links):
        ty = Inches(2.0) + i * Inches(0.72)
        add_textbox(s, Inches(7.0), ty, Inches(2.2), Inches(0.55),
                    name, font_size=14, bold=True, color=AMBER)
        add_textbox(s, Inches(9.3), ty, Inches(3.5), Inches(0.55),
                    desc, font_size=13, color=RGBColor(0xCC, 0xDD, 0xFF))

    # Tagline at bottom
    add_rect(s, Inches(0.3), Inches(6.5), Inches(12.7), Inches(0.72),
             RGBColor(0x00, 0x87, 0x8A))
    add_textbox(s, Inches(0.5), Inches(6.6), Inches(12.3), Inches(0.5),
                "Upload a .docx — get a conference-ready PDF in minutes.   "
                "python main.py  ·  open http://localhost:5173",
                font_size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    accent_bar(s, color=AMBER, height=Inches(0.05))
    slide_number(s, 12)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    prs = new_prs()

    slide_01_title(prs)
    slide_02_problem(prs)
    slide_03_what_it_is(prs)
    slide_04_architecture(prs)
    slide_05_conversion_pipeline(prs)
    slide_06_template_selection(prs)
    slide_07_edit_recompile(prs)
    slide_08_critic(prs)
    slide_09_security(prs)
    slide_10_deployment(prs)
    slide_11_demo(prs)
    slide_12_roadmap(prs)

    prs.save(OUTPUT)
    print(f"Saved: {OUTPUT}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
