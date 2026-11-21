#!/usr/bin/env python3
"""Gera o .docx do Estudo de Viabilidade (ABNT NBR 14724).

Uso:
    python3 scripts/generate_study_docx.py

Requisito: python-docx (pip install python-docx).
Saída: docs/estudo_viabilidade_abnt.docx
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
OUT = BASE / "docs" / "estudo_viabilidade_abnt.docx"


def estilo(doc: Document) -> None:
    s = doc.styles["Normal"]
    s.font.name = "Times New Roman"
    s.font.size = Pt(12)
    s.paragraph_format.line_spacing = 1.5
    s.paragraph_format.space_after = Pt(0)


def margens(doc: Document) -> None:
    for sec in doc.sections:
        sec.top_margin = Cm(3)
        sec.left_margin = Cm(3)
        sec.bottom_margin = Cm(2)
        sec.right_margin = Cm(2)


def titulo1(doc: Document, texto: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run(texto)
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)


def titulo2(doc: Document, texto: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(texto)
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)


def par(doc: Document, texto: str, recuo: bool = True) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(6)
    if recuo:
        p.paragraph_format.first_line_indent = Cm(1.25)
    r = p.add_run(texto)
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)


def legenda(doc: Document, texto: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(texto)
    r.font.name = "Times New Roman"
    r.font.size = Pt(10)


def tabela(doc: Document, linhas: list[tuple]) -> None:
    t = doc.add_table(rows=0, cols=len(linhas[0]))
    t.style = "Table Grid"
    for i, linha in enumerate(linhas):
        cells = t.add_row().cells
        for j, valor in enumerate(linha):
            cells[j].text = ""
            p = cells[j].paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(str(valor))
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.bold = (i == 0)


def referencias(doc: Document, refs: list[str]) -> None:
    titulo1(doc, "7 REFERÊNCIAS")
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run(ref)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)


# ---------------------------------------------------------------------------
def build() -> Document:
    doc = Document()
    margens(doc)
    estilo(doc)

    titulo1(doc, "ESTUDO DE VIABILIDADE — SOLUÇÃO ZERO TRUST ANTI-CHEAT")

    titulo1(doc, "1 OBJETIVO")
    par(doc,
        "Este estudo avalia a viabilidade técnica, operacional, econômica e ética da solução "
        "Zero Trust Anti-cheat construída ao longo do desenvolvimento da aplicação (backend "
        "Flask + frontend Tailwind + scanner de memória em três estágios), comparando-a com "
        "duas referências do mercado: o UltimateAntiCheat (open source, modo usuário) e o "
        "Valve Anti-Cheat (VAC), da Valve. O objetivo é responder se a solução é viável para "
        "o propósito a que se destina — detecção didática de cheats client-side em laboratório "
        "— e quais são suas fronteiras frente a soluções comerciais.")

    titulo1(doc, "2 O MODELO ZERO TRUST APLICADO AO ANTI-CHEAT")
    par(doc,
        "O princípio Zero Trust (\"nunca confie, sempre verifique\") parte da premissa de que "
        "nenhum elemento é confiável por padrão — inclusive o próprio cliente do jogador, que "
        "é justamente o elo onde o cheat atua. A solução desenvolvida materializa esse "
        "princípio no endpoint: não confia no cliente, verificando ativamente o estado do "
        "processo; realiza verificação contínua e multi-evidência (módulos injetados, "
        "integridade/hooks do opengl32.dll, artefatos e strings em memória), alimentando um "
        "veredito auditável com pontuação de ameaça; e opera em modo somente leitura, sem "
        "injetar ou modificar o processo. Trata-se, portanto, de um componente de verificação "
        "de endpoint inspirado no modelo Zero Trust, e não de uma arquitetura Zero Trust "
        "completa, que exigiria também um lado servidor.")

    titulo1(doc, "3 PANORAMA DE SOLUÇÕES COMPARÁVEIS")
    titulo2(doc, "3.1 UltimateAntiCheat")
    par(doc,
        "O UltimateAntiCheat, por ser open source e operar em modo usuário (user-mode), "
        "apresenta como principal vantagem a transparência e a possibilidade de estudo e "
        "modificação do código-fonte. Isso o torna adequado para fins educacionais e "
        "prototipagem. No entanto, sua segurança é limitada, sendo mais suscetível a técnicas "
        "de bypass, especialmente contra cheats mais avançados que operam em nível de kernel. "
        "Dessa forma, seu uso em ambientes de produção torna-se restrito (ALSCH092, 2023).")

    titulo2(doc, "3.2 Valve Anti-Cheat (VAC)")
    par(doc,
        "O Valve Anti-Cheat (VAC) é uma solução amplamente utilizada e reconhecida por sua "
        "escalabilidade e baixo impacto em performance (VALVE CORPORATION, 2003). Seu modelo "
        "de detecção baseado em assinaturas e heurísticas, aliado ao sistema de banimento "
        "tardio (delayed bans), permite identificar comportamentos suspeitos sem alertar "
        "imediatamente o usuário. Contudo, sua principal limitação está na complexidade de "
        "impedir cheats em tempo real, uma vez que o banimento é tardio e o modelo é "
        "predominantemente reativo (VALVE CORPORATION, 2003).")

    legenda(doc, "Quadro 1 — Síntese do panorama")
    tabela(doc, [
        ("Solução", "Licença/modo", "Vantagem central", "Limitação central", "Indicação"),
        ("UltimateAntiCheat", "Open source, user-mode", "Transparência e modificação", "Bypass por cheats em kernel-mode", "Educação e prototipagem"),
        ("Valve Anti-Cheat", "Proprietária (Steam)", "Escala e baixo overhead", "Reativa; banimento tardio", "Produção em larga escala"),
        ("Zero Trust (nossa)", "Acadêmica, somente leitura", "Evidência multiestágio auditável", "Client-side; assinaturas estáticas", "Ensino/laboratório"),
    ])

    titulo1(doc, "4 AVALIAÇÃO DA SOLUÇÃO DESENVOLVIDA")
    titulo2(doc, "4.1 Viabilidade técnica")
    par(doc,
        "A solução foi implementada e validada durante o desenvolvimento da aplicação: "
        "autenticação (login/registro, sessão, hash), dashboard e API REST, scanner em três "
        "estágios (A módulos, B detours/PE com parser próprio PE32/PE64, C artefatos/strings), "
        "backend duplo (real no Windows / demo fora dele) e banco autocurativo em SQLite. Nos "
        "cenários de teste, a varredura classificou corretamente o processo com o cheat v8 "
        "injetado como HACKEADO (score máximo) e o processo íntegro como LIMPO (score zero), "
        "além de emitir aviso quando o jogo não estava em execução. A viabilidade técnica "
        "está, portanto, comprovada para o escopo didático.")

    titulo2(doc, "4.2 Viabilidade operacional")
    par(doc,
        "O scan real depende do Windows e de privilégios equivalentes aos do jogo (leitura de "
        "memória de outro processo). A operação é simples: a interface web centraliza seleção "
        "de processo, execução da varredura, veredito e histórico, sem exigir linha de comando. "
        "O escopo de uso é o laboratório, offline contra bots, não pressupondo operação em "
        "servidores públicos.")

    titulo2(doc, "4.3 Viabilidade econômica")
    par(doc,
        "O custo de licenças é próximo de zero: a stack é integralmente gratuita e de código "
        "aberto (Python, Flask, SQLite, Tailwind e bibliotecas da stdlib), sem dependências "
        "pagas de SDK ou serviços de terceiros. O custo real concentra-se no esforço de "
        "desenvolvimento e em infraestrutura mínima (um host Windows para testes), sendo "
        "economicamente equivalente ao UltimateAntiCheat e muito inferior ao custo de "
        "licenciar/operar soluções proprietárias em larga escala.")

    titulo2(doc, "4.4 Viabilidade legal e ética")
    par(doc,
        "O artefato tem finalidade defensiva e acadêmica; o scanner é externo e somente "
        "leitura, não injetando nem modificando o processo. Recomenda-se execução em ambiente "
        "de laboratório, offline contra bots, evitando partidas protegidas por anti-cheats de "
        "terceiros. Sob essas condições, a solução é viável e aderente ao propósito do estudo.")

    titulo2(doc, "4.5 Riscos e limitações")
    tabela(doc, [
        ("Risco/limitação", "Impacto", "Mitigação possível"),
        ("Detecção client-side", "Não cobre cheats que evitam o processo", "Complementar com detecção server-side"),
        ("Assinaturas estáticas", "Cheats ofuscados/renomeados escapam", "Assinaturas atualizáveis (YAML/JSON)"),
        ("Falsos positivos (Estágio B)", "Divergência disco x memória isolada", "Priorizar mem[0]=0xE9 como evidência forte"),
        ("Dependência de privilégios", "Falha ao abrir o processo", "Execução elevada / documentação"),
        ("Bypass por user-mode", "Como no UltimateAntiCheat", "Escopo acadêmico; não é produto de produção"),
    ])

    titulo1(doc, "5 ANÁLISE COMPARATIVA")
    legenda(doc, "Quadro 2 — Comparação entre as soluções")
    tabela(doc, [
        ("Critério", "Zero Trust (nossa)", "UltimateAntiCheat", "VAC"),
        ("Licença", "Acadêmica", "Open source", "Proprietária"),
        ("Modo de operação", "Externo, somente leitura", "User-mode", "Integrado à Steam"),
        ("Detecção", "3 estágios + veredito/score", "Módulos, memória, debug", "Assinaturas + heurísticas"),
        ("Escalabilidade", "Baixa (didática)", "Baixa/média", "Alta"),
        ("Transparência", "Alta", "Alta", "Baixa"),
        ("Resistência a bypass", "Limitada", "Limitada", "Média/alta"),
        ("Tempo real", "Sim (pontual)", "Sim", "Reativo (delayed bans)"),
        ("Custo", "~zero", "~zero", "Licenciado"),
        ("Melhor uso", "Ensino/laboratório", "Prototipagem", "Produção em larga escala"),
    ])

    titulo1(doc, "6 PARECER DE VIABILIDADE")
    par(doc,
        "A solução Zero Trust Anti-cheat é viável para o propósito a que se propõe: "
        "tecnicamente (implementada, testada e com detecção correta nos cenários avaliados), "
        "economicamente (stack gratuita), operacionalmente (interface web simples em "
        "laboratório) e eticamente (escopo defensivo e somente leitura).")
    par(doc,
        "Como ressalva, a solução não substitui um anti-cheat de produção como o VAC. Ela é, "
        "por natureza, client-side e reativa em relação a assinaturas, com as mesmas "
        "fragilidades estruturais do UltimateAntiCheat frente a cheats em kernel-mode. Sua "
        "posição mais adequada é a de componente educacional e de verificação de endpoint, "
        "que idealmente se soma a uma camada server-side (heurísticas comportamentais: snap "
        "de mira, linha de visão, variância de tracking) para compor uma defesa em "
        "profundidade, coerente com o princípio Zero Trust de nunca confiar apenas em um "
        "único ponto de verificação. Conclui-se que a solução é viável para os fins do "
        "estudo, mas não recomendada como proteção única em produção.")

    referencias(doc, [
        "ALSCH092. UltimateAntiCheat: open source usermode anti-cheat system (C++, Windows). GitHub, [2023]. Disponível em: https://github.com/AlSch092/UltimateAntiCheat. Acesso em: 17 out. 2026.",
        "VALVE CORPORATION. Valve Anti-Cheat (VAC): sistema anti-cheat e banimentos de jogo. [S.l.]: Valve Corporation, 2003. Disponível em: https://partner.steamgames.com/doc/features/anticheat. Acesso em: 17 out. 2026.",
        "ZERO-TRUST-SYNDICATE. Anti-cheat v8: detecção client-side das técnicas do laboratório. [S.l.: s.n.], 2026. Disponível em: rebuild/v8/ANTICHEAT-v8.md. Acesso em: 17 out. 2026.",
        "ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. NBR 6023: informação e documentação — referências — elaboração. Rio de Janeiro: ABNT, 2018. 68 p.",
        "MICROSOFT. ReadProcessMemory function (memoryapi.h). 2024. Disponível em: https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory. Acesso em: 17 out. 2026.",
    ])

    return doc


def main() -> None:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(f"Estudo de viabilidade (ABNT) gerado em: {OUT}")


if __name__ == "__main__":
    main()
