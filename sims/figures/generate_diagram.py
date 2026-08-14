"""
generate_diagram.py
Generates a generic AI architecture diagram and saves it as both PDF and PNG.
Writes into templates/assets/figures/, where the conference templates'
sections/figures.tex expect to find them.

Run from anywhere:
    python sims/figures/generate_diagram.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(REPO_ROOT, "templates", "assets", "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Colour palette ───────────────────────────────────────────────────────────
C_INPUT   = "#4CAF50"   # green
C_PROC    = "#1976D2"   # blue
C_ATTN    = "#7B1FA2"   # purple
C_OUTPUT  = "#E53935"   # red
C_ARROW   = "#546E7A"   # slate
C_BG      = "#FAFAFA"

# ── Canvas ───────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5.5))
fig.patch.set_facecolor(C_BG)
ax.set_facecolor(C_BG)
ax.set_xlim(0, 13)
ax.set_ylim(0, 6)
ax.axis("off")

# ── Helper: draw a labelled box ──────────────────────────────────────────────
def box(ax, x, y, w, h, label, sublabel="", color="#1976D2", fontsize=11):
    rect = mpatches.FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.08",
        linewidth=1.5, edgecolor=color,
        facecolor=color + "22",   # transparent fill
        zorder=3,
    )
    ax.add_patch(rect)
    ax.text(x, y + (0.18 if sublabel else 0), label,
            ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color=color, zorder=4)
    if sublabel:
        ax.text(x, y - 0.28, sublabel,
                ha="center", va="center", fontsize=8.5,
                color=color, style="italic", zorder=4)

# ── Helper: draw an arrow ────────────────────────────────────────────────────
def arrow(ax, x1, x2, y, label=""):
    ax.annotate(
        "", xy=(x2, y), xytext=(x1, y),
        arrowprops=dict(arrowstyle="-|>", color=C_ARROW,
                        lw=1.6, mutation_scale=16),
        zorder=2,
    )
    if label:
        ax.text((x1 + x2) / 2, y + 0.22, label,
                ha="center", va="bottom", fontsize=8, color=C_ARROW)

# ── Helper: draw vertical arrow ──────────────────────────────────────────────
def varrow(ax, x, y1, y2, label=""):
    ax.annotate(
        "", xy=(x, y2), xytext=(x, y1),
        arrowprops=dict(arrowstyle="-|>", color=C_ARROW,
                        lw=1.4, mutation_scale=14),
        zorder=2,
    )
    if label:
        ax.text(x + 0.18, (y1 + y2) / 2, label,
                ha="left", va="center", fontsize=8, color=C_ARROW)

# ── Title ────────────────────────────────────────────────────────────────────
ax.text(6.5, 5.65, "Generic Deep Learning Architecture",
        ha="center", va="center", fontsize=14,
        fontweight="bold", color="#263238")

# ── Row y-positions ──────────────────────────────────────────────────────────
Y_MAIN = 3.2   # main pipeline row
Y_SUB  = 1.2   # sub-components row

# ── Main pipeline boxes ──────────────────────────────────────────────────────
# Input
box(ax, 1.0, Y_MAIN, 1.5, 1.1, "Input", "Raw Data", C_INPUT)

# Embedding
box(ax, 3.0, Y_MAIN, 1.5, 1.1, "Embedding", "d = 512", C_PROC)

# Encoder
box(ax, 5.2, Y_MAIN, 1.6, 1.1, "Encoder", "N × layers", C_PROC)

# Attention
box(ax, 7.5, Y_MAIN, 1.6, 1.1, "Attention", "Multi-Head", C_ATTN)

# Decoder
box(ax, 9.8, Y_MAIN, 1.6, 1.1, "Decoder", "N × layers", C_PROC)

# Output
box(ax, 12.0, Y_MAIN, 1.5, 1.1, "Output", "Softmax", C_OUTPUT)

# ── Main pipeline arrows ──────────────────────────────────────────────────────
arrow(ax, 1.76, 2.25, Y_MAIN, "tokens")
arrow(ax, 3.76, 4.40, Y_MAIN)
arrow(ax, 6.01, 6.69, Y_MAIN, "keys/values")
arrow(ax, 8.31, 9.00, Y_MAIN)
arrow(ax, 10.61, 11.25, Y_MAIN, "logits")

# ── Sub-components (Encoder internals) ───────────────────────────────────────
enc_x = 5.2
box(ax, enc_x - 0.55, Y_SUB, 0.9, 0.7, "Self-Attn", "", C_PROC, fontsize=8.5)
box(ax, enc_x + 0.55, Y_SUB, 0.9, 0.7, "FFN",        "", C_PROC, fontsize=8.5)
varrow(ax, enc_x - 0.55, Y_MAIN - 0.55, Y_SUB + 0.35)
varrow(ax, enc_x + 0.55, Y_MAIN - 0.55, Y_SUB + 0.35)
ax.annotate("", xy=(enc_x + 0.1, Y_SUB), xytext=(enc_x - 0.1, Y_SUB),
            arrowprops=dict(arrowstyle="-|>", color=C_ARROW, lw=1.2,
                            mutation_scale=12), zorder=2)

# ── Sub-components (Decoder internals) ───────────────────────────────────────
dec_x = 9.8
box(ax, dec_x - 0.55, Y_SUB, 0.9, 0.7, "Masked\nAttn", "", C_PROC, fontsize=7.5)
box(ax, dec_x + 0.55, Y_SUB, 0.9, 0.7, "Cross\nAttn",  "", C_PROC, fontsize=7.5)
varrow(ax, dec_x - 0.55, Y_MAIN - 0.55, Y_SUB + 0.35)
varrow(ax, dec_x + 0.55, Y_MAIN - 0.55, Y_SUB + 0.35)
ax.annotate("", xy=(dec_x + 0.1, Y_SUB), xytext=(dec_x - 0.1, Y_SUB),
            arrowprops=dict(arrowstyle="-|>", color=C_ARROW, lw=1.2,
                            mutation_scale=12), zorder=2)

# Cross-attention feed from encoder to decoder
ax.annotate(
    "", xy=(dec_x + 0.55, Y_SUB + 0.35), xytext=(enc_x, Y_MAIN - 0.55),
    arrowprops=dict(arrowstyle="-|>", color=C_ATTN, lw=1.2,
                    connectionstyle="arc3,rad=-0.25",
                    mutation_scale=13),
    zorder=2,
)
ax.text(7.5, 0.62, "encoder output", ha="center", va="center",
        fontsize=7.5, color=C_ATTN, style="italic")

# ── Legend ───────────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(facecolor=C_INPUT  + "33", edgecolor=C_INPUT,   label="I/O"),
    mpatches.Patch(facecolor=C_PROC   + "33", edgecolor=C_PROC,    label="Processing"),
    mpatches.Patch(facecolor=C_ATTN   + "33", edgecolor=C_ATTN,    label="Attention"),
    mpatches.Patch(facecolor=C_OUTPUT + "33", edgecolor=C_OUTPUT,  label="Output"),
]
ax.legend(handles=legend_items, loc="lower right", fontsize=8.5,
          framealpha=0.7, edgecolor="#CFD8DC")

plt.tight_layout(pad=0.4)

pdf_path = os.path.join(OUT_DIR, "ai_architecture.pdf")
png_path = os.path.join(OUT_DIR, "ai_architecture.png")
plt.savefig(pdf_path, bbox_inches="tight", dpi=150)
plt.savefig(png_path, bbox_inches="tight", dpi=150)
print(f"Saved: {pdf_path}")
print(f"Saved: {png_path}")
