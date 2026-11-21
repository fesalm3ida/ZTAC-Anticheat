#!/usr/bin/env python3
"""Gera um arquivo .docx com as referências da documentação de arquitetura,
formatadas segundo a ABNT NBR 6023.

Uso:
    python3 scripts/generate_references_docx.py

Requisito: python-docx (pip install python-docx).
Saída: docs/referencias_abnt.docx
"""
from __future__ import annotations

from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "python-docx não está instalado. Rode: pip install python-docx"
    ) from exc

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "docs" / "referencias_abnt.docx"

# Nome curto repetido era usado nos docs; acessado em (data de geração).
ACESSO = "1 set. 2026."
ANO_ACESSO = 2026

# ---------------------------------------------------------------------------
# Lista de referências (ABNT NBR 6023). O título entre ** ** fica em negrito.
# ---------------------------------------------------------------------------
REFERENCIAS = [
    "ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023: informação e documentação — referências — elaboração**. Rio de Janeiro: ABNT, 2018. 68 p.",
    "ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 14724: informação e documentação — trabalhos acadêmicos — apresentação**. Rio de Janeiro: ABNT, 2011. 113 p.",
    "ZERO-TRUST-SYNDICATE. **Anti-cheat v8: detecção client-side das técnicas do laboratório**. [S.l.: s.n.], 2026. Disponível em: rebuild/v8/ANTICHEAT-v8.md. Acesso em: 1 set. 2026.",
    "ZERO-TRUST-SYNDICATE. **Aimbot v8: guia de calibração e estudo de prevenção**. [S.l.: s.n.], 2026. Disponível em: doc/Aimbot-e-prevencao.md. Acesso em: 1 set. 2026.",
    "VALVE CORPORATION. **Counter-Strike 1.6** [software]. Bellevue: Valve Corporation, 2003.",
    "MICROSOFT. **ReadProcessMemory function (memoryapi.h)**. 2024. Disponível em: https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory. Acesso em: 1 set. 2026.",
    "MICROSOFT. **VirtualQueryEx function (memoryapi.h)**. 2024. Disponível em: https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualqueryex. Acesso em: 1 set. 2026.",
    "MICROSOFT. **CreateToolhelp32Snapshot function (tlhelp32.h)**. 2024. Disponível em: https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-createtoolhelp32snapshot. Acesso em: 1 set. 2026.",
    "MICROSOFT. **OpenProcess function (processthreadsapi.h)**. 2024. Disponível em: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess. Acesso em: 1 set. 2026.",
    "PALLETS. **Flask documentation**. 2024. Disponível em: https://flask.palletsprojects.com/. Acesso em: 1 set. 2026.",
    "TAILWIND LABS. **Tailwind CSS: utility-first CSS framework**. 2024. Disponível em: https://tailwindcss.com/docs. Acesso em: 1 set. 2026.",
    "MERMAID. **Mermaid: diagramming and charting tool**. 2024. Disponível em: https://mermaid.js.org/. Acesso em: 1 set. 2026.",
    "PYTHON SOFTWARE FOUNDATION. **sqlite3: SQLite databases**. Python 3.10.1 documentation. 2024. Disponível em: https://docs.python.org/3/library/sqlite3.html. Acesso em: 1 set. 2026.",
    "H J CHEATS. **Cheat para Counter-Strike** [software analisado]. 2025. Disponível em: https://dhjcheats.com/. Acesso em: 1 set. 2026.",
    "ALSCH092. **UltimateAntiCheat**: open source usermode anti-cheat system (C++, Windows). GitHub, [2023]. Disponível em: https://github.com/AlSch092/UltimateAntiCheat. Acesso em: 17 out. 2026.",
    "VALVE CORPORATION. **Valve Anti-Cheat (VAC)**: sistema anti-cheat e banimentos de jogo. [S.l.]: Valve Corporation, 2003. Disponível em: https://partner.steamgames.com/doc/features/anticheat. Acesso em: 17 out. 2026.",
]


def add_bold_runs(paragraph, text: str) -> None:
    """Adiciona runs ao parágrafo, aplicando negrito ao texto entre ** **."""
    import re

    for i, chunk in enumerate(re.split(r"(\*\*.*?\*\*)", text)):
        if not chunk:
            continue
        bold = chunk.startswith("**") and chunk.endswith("**")
        content = chunk[2:-2] if bold else chunk
        run = paragraph.add_run(content)
        run.bold = bold
        run.font.size = Pt(12)
        run.font.name = "Times New Roman"


def build() -> Document:
    doc = Document()

    # Margens ABNT (superior/esquerda 3cm, inferior/direita 2cm)
    for section in doc.sections:
        section.top_margin = Pt(85)          # ~3 cm
        section.left_margin = Pt(85)
        section.bottom_margin = Pt(57)       # ~2 cm
        section.right_margin = Pt(57)

    # Fonte padrão do corpo
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    # Cabeçalho do documento
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("REFERÊNCIAS")
    r.bold = True
    r.font.size = Pt(14)
    r.font.name = "Times New Roman"
    r.font.color.rgb = RGBColor(0, 0, 0)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("Documentação de arquitetura do anti-cheat (Flask + Tailwind)")
    r.font.size = Pt(11)
    r.font.name = "Times New Roman"

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = meta.add_run("Norma: ABNT NBR 6023, " + str(ANO_ACESSO))
    r.font.size = Pt(10)
    r.font.name = "Times New Roman"
    meta.paragraph_format.space_after = Pt(18)

    # Lista de referências
    for ref in REFERENCIAS:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(12)
        p.paragraph_format.space_before = Pt(0)
        # Entrecitação ABNT: alinhado à esquerda, sem recuo de primeira linha.
        p.paragraph_format.left_indent = Pt(0)
        p.paragraph_format.first_line_indent = Pt(0)
        add_bold_runs(p, ref)

    return doc


def main() -> None:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(f"Referências em ABNT NBR 6023 geradas em: {OUT}")


if __name__ == "__main__":
    main()
