from __future__ import annotations

from pathlib import Path

import typer

from .config import DEFAULT_TEMPLATE
from .converter import ConversionError, ConversionOptions, convert_document
from .templates import is_valid_template, valid_template_ids

app = typer.Typer(help="CLI utilities for converting Word docs into LaTeX workspaces.")


@app.command()
def convert(
    docx: Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to the .docx file."),
    template: str = typer.Option(DEFAULT_TEMPLATE, "--template", "-t", help="Template directory under latex/"),
    no_build: bool = typer.Option(False, help="Skip LaTeX PDF build step."),
):
    """Convert DOCX into a LaTeX workspace using a given template."""

    if not is_valid_template(template):
        typer.secho(
            f"Invalid template '{template}'. Choose from: {', '.join(valid_template_ids()) or '(none found)'}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    try:
        manifest = convert_document(docx, ConversionOptions(template=template, build_pdf=not no_build))
    except ConversionError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Created workspace: documents/{manifest.document_id}")


if __name__ == "__main__":  # pragma: no cover
    app()
