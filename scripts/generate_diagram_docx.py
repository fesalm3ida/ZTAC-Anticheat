#!/usr/bin/env python3
"""Gera docs/diagrama_componentes.docx com o diagrama (PNG) embutido.

O Word NÃO renderiza HTML ao vivo; a forma correta de inserir o diagrama é
como IMAGEM (este script faz isso) ou como HIPERLINK para o arquivo.

Uso:
    python3 scripts/generate_diagram_docx.py

Requisitos: python-docx  e o PNG em docs/diagrama_componentes.png
(o PNG é gerado a partir de docs/diagrama_componentes.mmd via mermaid.ink).
"""
from __future__ import annotations

from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt
except ImportError as exc:  # pragma: no cover
    raise SystemExit("python-docx não está instalado. Rode: pip install python-docx") from exc

BASE = Path(__file__).resolve().parent.parent
PNG = BASE / "docs" / "diagrama_componentes.png"
OUT = BASE / "docs" / "diagrama_componentes.docx"


def main() -> None:
    if not PNG.exists():
        raise SystemExit(f"PNG não encontrado: {PNG}")

    doc = Document()

    # Página A4 com margens ABNT (sup/esq 3 cm, inf/dir 2 cm)
    for sec in doc.sections:
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.top_margin = Cm(3)
        sec.left_margin = Cm(3)
        sec.bottom_margin = Cm(2)
        sec.right_margin = Cm(2)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.5

    # Título
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run("Diagrama de componentes — Anti-cheat web (CS 1.6)")
    r.bold = True
    r.font.size = Pt(14)
    r.font.name = "Times New Roman"

    # Legenda da figura (acima, conforme NBR 14724)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(12)
    cap.paragraph_format.space_after = Pt(6)
    r = cap.add_run(
        "Figura 1 — Arquitetura em três camadas: apresentação, aplicação e detecção."
    )
    r.font.size = Pt(10)
    r.font.name = "Times New Roman"

    # Imagem centralizada, largura útil de 16 cm
    pic_par = doc.add_paragraph()
    pic_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_par.paragraph_format.space_after = Pt(4)
    pic_par.add_run().add_picture(str(PNG), width=Cm(16))

    # Fonte (abaixo da figura)
    src = doc.add_paragraph()
    src.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = src.add_run("Fonte: elaborado pelos autores (2026).")
    r.font.size = Pt(10)
    r.font.name = "Times New Roman"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(f"DOCX com o diagrama embutido gerado em: {OUT}")


if __name__ == "__main__":
    main()
