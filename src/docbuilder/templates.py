"""Template registry — the single source of truth for which LaTeX templates exist.

A template is a directory under ``templates/latex/<id>/`` that contains a ``main.tex``.
It is considered *buildable* only when a matching build script
``scripts/templates/<id>/build.sh`` also exists. Directories whose name starts with an
underscore (``_vendor/``) hold upstream author kits and are never templates. The docserver, converter, and CLI all consult these helpers so the set of
valid templates is discovered from the filesystem rather than hardcoded.
"""

from __future__ import annotations

from .config import LATEX_ROOT, SCRIPT_ROOT
from .models import TemplateInfo

# Optional display metadata per template id. Missing ids fall back to ``id.upper()``
# for the name and ``None`` for the description.
TEMPLATE_METADATA: dict[str, dict[str, str]] = {
    "ieee": {"name": "IEEE Conference", "description": "IEEEtran two-column conference format"},
    "acm": {"name": "ACM (acmart)", "description": "ACM acmart article format"},
    "neurips": {"name": "NeurIPS 2025", "description": "NeurIPS 2025 single-column style"},
    "aaai": {"name": "AAAI 2026", "description": "AAAI 2026 author-kit format"},
}


def _build_script_exists(template_id: str) -> bool:
    return (SCRIPT_ROOT / template_id / "build.sh").exists()


def available_templates() -> list[TemplateInfo]:
    """Discover templates on disk, sorted by id.

    Includes any ``templates/latex/<id>/`` directory containing a ``main.tex``. Each is flagged
    ``buildable`` based on whether its build script is present.
    """
    if not LATEX_ROOT.exists():
        return []

    templates: list[TemplateInfo] = []
    for path in sorted(LATEX_ROOT.iterdir(), key=lambda p: p.name):
        if path.name.startswith("_"):
            continue
        if not path.is_dir() or not (path / "main.tex").exists():
            continue
        meta = TEMPLATE_METADATA.get(path.name, {})
        templates.append(
            TemplateInfo(
                id=path.name,
                name=meta.get("name", path.name.upper()),
                description=meta.get("description"),
                buildable=_build_script_exists(path.name),
            )
        )
    return templates


def valid_template_ids() -> list[str]:
    """Sorted ids of all discoverable templates (regardless of buildability)."""
    return [t.id for t in available_templates()]


def is_valid_template(template_id: str) -> bool:
    return template_id in valid_template_ids()


def is_buildable(template_id: str) -> bool:
    return any(t.id == template_id and t.buildable for t in available_templates())
