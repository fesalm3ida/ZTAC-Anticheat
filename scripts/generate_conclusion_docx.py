#!/usr/bin/env python3
"""Gera o .docx da Conclusão e das Considerações Finais (incluindo a stack),
formatado segundo a ABNT NBR 14724.

Uso:
    python3 scripts/generate_conclusion_docx.py

Requisito: python-docx (pip install python-docx).
Saída: docs/conclusao_consideracoes_abnt.docx

Formatação aplicada (NBR 14724):
  - margens: superior/esquerda 3 cm, inferior/direita 2 cm
  - fonte: Times New Roman 12
  - corpo: espaço entre linhas 1,5; justificado; recuo de 1,25 cm
  - títulos de seção primária: MAIÚSCULAS, negrito, alinhados à esquerda
  - títulos de seção secundária: negrito, somente inicial maiúscula
"""
from __future__ import annotations

from pathlib import Path

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "python-docx não está instalado. Rode: pip install python-docx"
    ) from exc

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "docs" / "conclusao_consideracoes_abnt.docx"

# ---------------------------------------------------------------------------
# Conteúdo
# ---------------------------------------------------------------------------
CONCLUSAO = [
    "O projeto teve como objetivo construir um anti-cheat com interface gráfica "
    "capaz de identificar, de forma automatizada, cheats que atuam no processo do "
    "Counter-Strike 1.6, a partir da análise de anomalias em memória. O objetivo foi "
    "alcançado: o sistema integra, em uma única aplicação web, autenticação de "
    "usuários, orquestração da varredura, execução dos três estágios de detecção "
    "herdados do anti-cheat v8 e a apresentação do veredito na interface gráfica.",

    "Do ponto de vista funcional, o ciclo completo previsto foi implementado: o "
    "usuário autentica-se, seleciona — ou limpa — o processo alvo, dispara a "
    "varredura e recebe um relatório com veredito (LIMPO, SUSPEITO ou HACKEADO), "
    "pontuação de ameaça e os achados agrupados por estágio, além do histórico "
    "persistido. Nos cenários avaliados, a varredura classificou corretamente um "
    "processo com o cheat v8 injetado como HACKEADO (score máximo) e um processo "
    "íntegro como LIMPO (score zero), comprovando a eficácia das assinaturas. O "
    "tratamento do caso em que o jogo não está em execução — que passou a emitir um "
    "aviso explícito em vez de um resultado enganoso — reforça a confiabilidade do "
    "fluxo.",

    "A detecção apoia-se em três evidências complementares — módulos injetados "
    "(Estágio A), integridade e hooks do opengl32.dll (Estágio B) e artefatos e "
    "strings em memória (Estágio C) — o que confere robustez ao veredito: técnicas "
    "distintas do mesmo cheat produzem evidências independentes, dificultando a "
    "evasão por meio de uma única alteração.",

    "Conclui-se que a combinação de um scanner externo (somente leitura, sem "
    "injeção) com uma camada web de apresentação mostra-se viável e adequada ao "
    "propósito didático do estudo, permitindo observar e documentar a assinatura das "
    "técnicas empregadas. Ressalta-se, contudo, que o alcance é client-side e depende "
    "de privilégios equivalentes aos do jogo, conforme discutido nas considerações a "
    "seguir.",
]

# (título, [parágrafos])
CONSIDERACOES = [
    ("7.1 Stack do projeto", [
        "A solução foi construída inteiramente sobre tecnologias gratuitas e de "
        "código aberto, priorizando portabilidade e ausência de dependências pesadas. "
        "A Tabela 1 resume a stack empregada.",
    ]),
]

STACK_TABLE = [
    ("Camada", "Tecnologia", "Versão", "Papel no projeto"),
    ("Linguagem", "Python", "3.10", "Backend, scanner e scripts auxiliares"),
    ("Framework web", "Flask", "3.0", "Rotas de página, API REST e inicialização"),
    ("WSGI / segurança", "Werkzeug", "3.0", "Hash de senha (PBKDF2) e sessão assinada"),
    ("Templates", "Jinja2 (via Flask)", "3.1", "Renderização das páginas HTML"),
    ("Estilização", "Tailwind CSS (CDN)", "3.x", "Dashboard e telas de acesso"),
    ("Interatividade", "JavaScript (Fetch API)", "ES6+", "Consumo da API e render dinâmico"),
    ("Persistência", "SQLite (sqlite3)", "stdlib", "Usuários e histórico de varreduras"),
    ("Acesso ao SO", "ctypes -> kernel32", "stdlib", "Processos, módulos e leitura de memória"),
    ("Parsing binário", "struct", "stdlib", "Cabeçalhos PE: exports e RVA->offset"),
    ("Diagramas", "Mermaid", "11", "Diagrama de arquitetura"),
    ("Geração de DOCX", "python-docx", "1.2", "Referências e conclusão em ABNT"),
    ("Versionamento", "Git", "-", "Controle de versão do projeto"),
]

POS_TABELA = [
    "As APIs de sistema utilizadas no Windows são CreateToolhelp32Snapshot, "
    "OpenProcess, VirtualQueryEx, ReadProcessMemory e CloseHandle. O alvo é o "
    "Counter-Strike 1.6 (engine GoldSrc), nos processos hl.exe e cstrike.exe.",
]

CONTRIBUICOES = [
    "Reaproveitamento das assinaturas do v8 em uma arquitetura web, separando a "
    "lógica de detecção (signatures.py) da mecânica de leitura de memória.",

    "Backend duplo com seleção automática: scan real no Windows e modo simulado fora "
    "dele, o que viabiliza desenvolver e testar toda a interface sem um processo do "
    "jogo — decisão que reduziu o acoplamento entre interface e sistema operacional.",

    "Parser de PE próprio (PE32/PE64), que torna o Estágio B independente de "
    "bibliotecas externas.",

    "Banco autocurativo, que elimina falhas de esquema em tempo de execução.",

    "Fluxo de varredura explícito, com limpeza de processo e aviso dedicado quando o "
    "jogo não está em execução.",
]

LIMITACOES = [
    "Escopo client-side: o sistema detecta o cheat na máquina do jogador; não "
    "substitui a detecção server-side (comportamento, snap de mira, linha de visão).",

    "Dependência de privilégios: a leitura de memória exige permissão equivalente à "
    "do jogo (ou elevação), o que pode exigir execução como administrador.",

    "Falsos positivos no Estágio B: relocações de PE podem alterar bytes entre disco "
    "e memória; por isso o veredito mais forte é mem[0] = 0xE9, enquanto a "
    "divergência isolada é tratada como suspeita.",

    "Assinaturas estáticas: a detecção depende de padrões conhecidos; cheats "
    "ofuscados ou renomeados podem escapar até que novas assinaturas sejam "
    "adicionadas.",

    "Modo demo não substitui o teste real: ele exercita a interface e o pipeline, "
    "mas a validação das assinaturas de memória só ocorre no Windows.",
]

FUTUROS = [
    "Detecção server-side (plugin AMX Mod X) com heurísticas de comportamento.",
    "Assinaturas configuráveis em YAML/JSON, atualizáveis sem recompilar.",
    "Correlação entre os logs do cheat e os dados observados pelo servidor.",
    "Testes automatizados (unitários do parser de PE e do cálculo de veredito).",
    "Endurecimento da autenticação (perfis de acesso, expiração, HTTPS).",
    "Empacotamento da aplicação para implantação simplificada.",
]

ETICA = [
    "O artefato foi desenvolvido com finalidade defensiva e acadêmica, para observar "
    "e documentar assinaturas de cheats no âmbito do estudo Zero-Trust-Syndicate. O "
    "scanner é externo e somente leitura: não injeta código, não modifica o processo "
    "do jogo e não interfere na jogabilidade. Os testes devem ser conduzidos em "
    "ambiente de laboratório, offline contra bots, evitando partidas online "
    "protegidas por anti-cheats, tanto por questões éticas quanto para preservar a "
    "validade do experimento.",
]


# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------
def configurar_estilo(doc: Document) -> None:
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    pf = style.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)


def configurar_margens(doc: Document) -> None:
    for s in doc.sections:
        s.top_margin = Cm(3)
        s.left_margin = Cm(3)
        s.bottom_margin = Cm(2)
        s.right_margin = Cm(2)


def titulo_primario(doc: Document, texto: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run(texto)
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)


def titulo_secundario(doc: Document, texto: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(texto)
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)


def paragrafo(doc: Document, texto: str, recuo: bool = True) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(6)
    if recuo:
        p.paragraph_format.first_line_indent = Cm(1.25)
    r = p.add_run(texto)
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)


def lista(doc: Document, itens: list[str]) -> None:
    for item in itens:
        p = doc.add_paragraph(style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(item)
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


def tabela_stack(doc: Document) -> None:
    t = doc.add_table(rows=0, cols=4)
    t.style = "Table Grid"
    for i, linha in enumerate(STACK_TABLE):
        cells = t.add_row().cells
        for j, valor in enumerate(linha):
            cells[j].text = ""
            p = cells[j].paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(valor)
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.bold = (i == 0)


# ---------------------------------------------------------------------------
def build() -> Document:
    doc = Document()
    configurar_margens(doc)
    configurar_estilo(doc)

    # 6 CONCLUSÃO
    titulo_primario(doc, "6 CONCLUSÃO")
    for p in CONCLUSAO:
        paragrafo(doc, p)

    doc.add_page_break()

    # 7 CONSIDERAÇÕES FINAIS
    titulo_primario(doc, "7 CONSIDERAÇÕES FINAIS")

    titulo_secundario(doc, "7.1 Stack do projeto")
    for p in CONSIDERACOES[0][1]:
        paragrafo(doc, p)
    legenda(doc, "Tabela 1 — Stack tecnológica do projeto")
    tabela_stack(doc)
    for p in POS_TABELA:
        paragrafo(doc, p)

    titulo_secundario(doc, "7.2 Contribuições")
    lista(doc, CONTRIBUICOES)

    titulo_secundario(doc, "7.3 Limitações")
    lista(doc, LIMITACOES)

    titulo_secundario(doc, "7.4 Trabalhos futuros")
    lista(doc, FUTUROS)

    titulo_secundario(doc, "7.5 Considerações éticas e de escopo")
    for p in ETICA:
        paragrafo(doc, p)

    return doc


def main() -> None:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(f"Conclusão e Considerações Finais (ABNT) geradas em: {OUT}")


if __name__ == "__main__":
    main()
