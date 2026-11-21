# Arquitetura do anti-cheat

Este documento descreve a arquitetura do **anti-cheat web** (Flask + Tailwind),
com diagrama em Mermaid, uma versão em ASCII para terminal e o detalhamento de
cada camada.

- Diagrama **Mermaid** (renderiza em GitHub/GitLab/VS Code): abaixo.
- Diagrama **interativo** no navegador: [`architecture.html`](architecture.html).
- Implantação e configuração: [deployment.md](deployment.md).

---

## 1. Diagrama da arquitetura

```mermaid
flowchart TD
    U[/"Usuário<br/>Navegador · Tailwind CDN<br/>login · registro · dashboard"/]
    U -->|"HTTP — páginas + JSON"| WEB

    subgraph FLASK["Servlet Flask (anticheat/)"]
        WEB["web.py · fábrica do app<br/>rotas de página /login /register /"]
        API["api.py · Blueprint REST<br/>/api/*"]
        AUTH["auth.py · sessão assinada<br/>hash werkzeug"]
        DB[("db.py · SQLite<br/>usuários + histórico scans")]
        FACT["scanner/__init__.py<br/>create_scanner()"]
    end

    WEB --> API
    API --> AUTH
    API --> DB
    API --> FACT

    FACT -->|"os.name == 'nt'"| WS
    FACT -->|"WSL/Linux ou AC_FORCE_DEMO=1"| SS

    subgraph BACKEND["Backend de varredura"]
        WS["WindowsScanner · real<br/>ctypes → kernel32/ntdll<br/>scanner/windows_scanner.py"]
        SS["SimulatedScanner · demo<br/>dados sintéticos p/ UI<br/>scanner/simulated_scanner.py"]
        PE["pe_parser.py · parser de PE<br/>exports + RVA→offset"]
        SIG["signatures.py · assinaturas v8"]
    end

    subgraph DETECCAO["Estágios de detecção"]
        SA["Estágio A — Módulos injetados"]
        SB["Estágio B — Detours / integridade"]
        SC["Estágio C — Artefatos & strings"]
    end

    WS --> SA & SB & SC
    SB --> PE
    WS & SS --> SIG
    WS -->|"ReadProcessMemory / VirtualQueryEx"| GAME
    GAME[("Processo do jogo · Windows<br/>hl.exe / cstrike.exe<br/>memória, módulos, opengl32.dll")]

    SA --> RS[("ScanReport<br/>veredito · score · findings<br/>base.py")]
    SB --> RS
    SC --> RS
    SS --> RS
    RS --> DB
```

---

## 2. Versão em ASCII (terminal)

```
                          ┌───────────────────────────────────────┐
                          │        USUÁRIO (navegador)            │
                          │  Tailwind CDN · login · dashboard     │
                          └───────────────────┬───────────────────┘
                                              │  HTTP (páginas + JSON)
                                              ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                       SERVIDOR FLASK (anticheat/)                 │
   │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
   │  │   web.py     │  │  api.py      │  │        auth.py         │  │
   │  │ rotas página │─▶│ Blueprint    │─▶│ sessão assinada + hash │  │
   │  │ /login  /    │  │ /api/*       │  └────────────────────────┘  │
   │  └──────────────┘  └──────┬───────┘                               │
   │                           │                                       │
   │              ┌────────────▼────────────┐       ┌──────────────┐   │
   │              │  db.py · SQLite         │       │   FACTORY    │   │
   │              │  usuários + scans       │       │ create_scanner│   │
   │              └─────────────────────────┘       └──────┬───────┘   │
   └──────────────────────────────────────────────────────┼───────────┘
                                                          │
                                   os.name == 'nt' ?  ┌───┴────┐
                              ┌────────────────────────┘        └──────────────────┐
                     ┌────────▼─────────────────┐                  ┌───────────────▼─────────┐
                     │  WindowsScanner (real)   │                  │ SimulatedScanner (demo)   │
                     │  ctypes → kernel32       │                  │ dados sintéticos p/ UI    │
                     │  + pe_parser + assinaturas│                └───────────────────┬───────┘
                     └────────┬─────────────────┘                                      │
                              │ ReadProcessMemory / VirtualQueryEx                     │
                              ▼                                                       │
                     ┌──────────────────────────┐                                     │
                     │  Jogo CS 1.6 (Windows)  │                                     │
                     │  hl.exe / cstrike.exe   │                                     │
                     │  módulos · memória ·   │                                     │
                     │  opengl32.dll          │                                     │
                     └──────────────────────────┘                                     │
                                                                                     │
   Estágio A · B · C  ────────────────► ScanReport (veredito, score, findings) ◄─────┘
```

---

## 3. Camadas em detalhe

### 3.1 Apresentação (browser)
- **Tailwind (via CDN) + Jinja** (`templates/`): `login.html`, `register.html`,
  `dashboard.html`, `base.html`.
- **`static/app.js`** consome a API e renderiza veredito, score, resultados por
  estágio e histórico. **`static/auth.js`** gerencia login/registro.

### 3.2 Aplicação (Flask)
- **`web.py`**: cria o app, configura secret_key/sessão, registra o blueprint e
  serve as páginas. Protege `/` com `login_required`.
- **`api.py`**: Blueprint REST (`/api/register|login|logout|me|processes|scan|
  reports`). É o único ponto que fala com o scanner e o banco.
- **`auth.py`**: registro/validação de credenciais, hash (werkzeug/PBKDF2),
  decorator `login_required` (redireciona na web, 401 na API).

### 3.3 Dados
- **`db.py`** (SQLite): tabelas `users` e `scans`. Guarda o relatório JSON de
  cada varredura para o histórico. Caminho padrão `data/anticheat.db`.

### 3.4 Varredura (o núcleo)
- **Fábrica** (`scanner/__init__.py`): seleciona o backend por SO/flag.
- **Backends**:
  - **`WindowsScanner`** (real): lê o processo do jogo usando
    `CreateToolhelp32Snapshot`, `OpenProcess`, `VirtualQueryEx`, `ReadProcessMemory`.
  - **`SimulatedScanner`** (demo): gera um `ScanReport` idêntico para testar a
    GUI sem processo do Windows.
- **Assinaturas** (`signatures.py`): lista negra de módulos, alvos de hook do
  `opengl32.dll`, strings de memória e artefatos — herdadas do anti-cheat v8.
- **Parser de PE** (`pe_parser.py`): lê exports e converte RVA→offset, usado no
  Estágio B para comparar bytes em disco × memória.
- **`base.py`**: `ScannerBase` (interface), `Finding` e `ScanReport` com o
  cálculo de veredito/score.

### 3.5 Detecção (3 estágios)
- **A — Módulos:** DLLs injetadas / fora da whitelist / nome "hex aleatório".
- **B — Detours:** `mem[0]==0xE9` (detour inline) ou bytes divergentes em
  exports do `opengl32.dll` (`wglSwapBuffers`, `glBegin`, `glEnable`, …).
- **C — Artefatos & strings:** logs em `C:\Temp\*_Debug.txt` e assinaturas na
  memória (`AIMBOT PRONTO`, `ForceWallhack`, `hk_wglSwapBuffers`, `gEngfuncs`).

---

## 4. Fluxo de uma varredura

1. O usuário autentica (cookie de sessão assinada) e clica em **Iniciar varredura**.
2. `app.js` faz `POST /api/scan` (com o `pid` do processo selecionado).
3. `api.py` chama `create_scanner()` (Windows real ou demo) e `scan(pid)`.
4. O scanner enumera módulos, parseia o `opengl32.dll`, lê memória e coleta
   artifacts/strings → monta um `ScanReport`.
5. `base.py` calcula **score** (peso por severidade) e **veredito**
   (LIMPO / SUSPEITO / HACKEADO).
6. A API salva o relatório em `scans` (histórico) e devolve o JSON.
7. `app.js` renderiza veredito, barra de ameaça, achados por estágio e
   atualiza o histórico.

---

## 5. Decisões de arquitetura

| Decisão | Racional |
|---|---|
| **Backend Python puro (ctypes)** em vez de compilar o C++ v8 | Portável, sem toolchain MinGW; mesmo efeito com menos fricção. |
| **Seleção automática do backend** | O scan real só roda no Windows; o demo permite desenvolver/testar a UI em WSL/Linux sem processo do jogo. |
| **Sessão assinada por cookie** | Sem dependência de servidor de sessão; funciona igual no Windows e WSL. |
| **SQLite** | Zero-config, arquivo local; suficiente para usuários + histórico. |
| **Assinaturas centralizadas** (`signatures.py`) | Fácil de estender/atualizar sem mexer na lógica de detecção. |
| **Scan externo (somente leitura)** | Não injeta nada; alinhado ao escopo defensivo do laboratório. |

> Diagrama interativo: abra [`architecture.html`](architecture.html) no navegador.

---

## 6. Conclusão

> Versão em DOCX (ABNT NBR 14724): [`conclusao_consideracoes_abnt.docx`](conclusao_consideracoes_abnt.docx),
> gerada por [`scripts/generate_conclusion_docx.py`](../scripts/generate_conclusion_docx.py).

O projeto teve como objetivo construir um anti-cheat com interface gráfica
capaz de identificar, de forma automatizada, cheats que atuam no processo do
Counter-Strike 1.6, a partir da análise de anomalias em memória. **O objetivo
foi alcançado**: o sistema integra, em uma única aplicação web, autenticação de
usuários, orquestração da varredura, execução dos três estágios de detecção
herdados do anti-cheat v8 e a apresentação do veredito na interface gráfica.

Do ponto de vista funcional, o ciclo completo previsto foi implementado: o
usuário autentica-se, seleciona — ou limpa — o processo alvo, dispara a
varredura e recebe um relatório com **veredito** (LIMPO, SUSPEITO ou
HACKEADO), **pontuação de ameaça** e os **achados agrupados por estágio**,
além do histórico persistido. Nos cenários avaliados, a varredura classificou
corretamente um processo com o cheat v8 injetado como `HACKEADO` (score
máximo) e um processo íntegro como `LIMPO` (score zero), comprovando a
eficácia das assinaturas. O tratamento do caso em que o jogo não está em
execução — que passou a emitir um aviso explícito em vez de um resultado
enganoso — reforça a confiabilidade do fluxo.

A detecção apoia-se em três evidências complementares — módulos injetados
(Estágio A), integridade e hooks do `opengl32.dll` (Estágio B) e artefatos e
strings em memória (Estágio C) — o que confere robustez ao veredito: técnicas
distintas do mesmo cheat produzem evidências independentes, dificultando a
evasão por meio de uma única alteração.

Conclui-se que a combinação de um **scanner externo** (somente leitura, sem
injeção) com uma **camada web de apresentação** mostra-se viável e adequada ao
propósito didático do estudo, permitindo observar e documentar a assinatura
das técnicas empregadas. Ressalta-se, contudo, que o alcance é *client-side* e
depende de privilégios equivalentes aos do jogo, conforme discutido a seguir.

---

## 7. Considerações Finais

### 7.1 Stack do projeto

A solução foi construída inteiramente sobre tecnologias gratuitas e de código
aberto, priorizando portabilidade e ausência de dependências pesadas.

| Camada | Tecnologia | Versão | Papel no projeto |
|---|---|---|---|
| Linguagem | **Python** | 3.10 | Backend, scanner e scripts auxiliares |
| Framework web | **Flask** | 3.0 | Rotas de página, API REST e inicialização |
| WSGI / segurança | **Werkzeug** | 3.0 | Hash de senha (PBKDF2) e sessão assinada |
| Templates | **Jinja2** (via Flask) | 3.1 | Renderização das páginas HTML |
| Estilização | **Tailwind CSS** (CDN) | 3.x | Interface do dashboard e telas de acesso |
| Interatividade | **JavaScript** (Fetch API) | ES6+ | Consumo da API e render dinâmico (sem framework) |
| Persistência | **SQLite** (`sqlite3`) | stdlib | Usuários e histórico de varreduras |
| Acesso ao SO | **`ctypes`** → `kernel32` | stdlib | Enumeração de processos/módulos e leitura de memória |
| Parsing binário | **`struct`** | stdlib | Cabeçalhos PE: exports e RVA→offset |
| Diagramas | **Mermaid** | 11 | Diagrama de arquitetura |
| Geração de DOCX | **python-docx** | 1.2 | Referências no padrão ABNT |
| Versionamento | **Git** | — | Controle de versão do projeto |

**APIs de sistema utilizadas (Windows):** `CreateToolhelp32Snapshot`,
`OpenProcess`, `VirtualQueryEx`, `ReadProcessMemory` e `CloseHandle`.
**Alvo:** Counter-Strike 1.6 (engine GoldSrc), processos `hl.exe` / `cstrike.exe`.

### 7.2 Contribuições

- **Reaproveitamento das assinaturas do v8** em uma arquitetura web, separando
  a lógica de detecção (`signatures.py`) da mecânica de leitura de memória.
- **Backend duplo com seleção automática**: scan real no Windows e modo
  simulado fora dele, o que viabiliza desenvolver e testar toda a interface
  sem um processo do jogo — decisão que reduziu o acoplamento entre UI e SO.
- **Parser de PE próprio** (PE32/PE64), que torna o Estágio B independente de
  bibliotecas externas.
- **Banco autocurativo**, que elimina falhas de esquema em tempo de execução.
- **Fluxo de varredura explícito**, com limpeza de processo e aviso dedicado
  quando o jogo não está em execução.

### 7.3 Limitações

- **Escopo client-side**: o sistema detecta o cheat na máquina do jogador; não
  substitui a detecção *server-side* (comportamento, snap de mira, linha de
  visão).
- **Dependência de privilégios**: a leitura de memória exige permissão
  equivalente à do jogo (ou elevação), o que pode exigir execução como
  administrador.
- **Falsos positivos no Estágio B**: relocações de PE podem alterar bytes entre
  disco e memória; por isso o veredito mais forte é `mem[0] == 0xE9`, enquanto a
  divergência isolada é tratada como suspeita.
- **Assinaturas estáticas**: a detecção depende de padrões conhecidos; cheats
  ofuscados ou renomeados podem escapar até que novas assinaturas sejam
  adicionadas.
- **Modo demo não substitui o teste real**: ele exercita a interface e o
  pipeline, mas a validação das assinaturas de memória só ocorre no Windows.

### 7.4 Trabalhos futuros

1. **Detecção server-side** (plugin AMX Mod X) com heurísticas de comportamento.
2. **Assinaturas configuráveis** em YAML/JSON, atualizáveis sem recompilar.
3. **Correlação** entre os logs do cheat e os dados observados pelo servidor.
4. **Testes automatizados** (unitários do parser de PE e do cálculo de veredito).
5. **Endurecimento da autenticação** (perfis de acesso, expiração, HTTPS).
6. **Empacotamento** da aplicação para implantação simplificada.

### 7.5 Considerações éticas e de escopo

O artefato foi desenvolvido com **finalidade defensiva e acadêmica**, para
observar e documentar assinaturas de cheats no âmbito do estudo
Zero-Trust-Syndicate. O scanner é **externo e somente leitura**: não injeta
código, não modifica o processo do jogo e não interfere na jogabilidade. Os
testes devem ser conduzidos em **ambiente de laboratório, offline contra bots**,
evitando partidas online protegidas por anti-cheats, tanto por questões éticas
quanto para preservar a validade do experimento.

---

## 8. Referências

> Formatação conforme a **ABNT NBR 6023**. Versão em DOCX:
> [`referencias_abnt.docx`](referencias_abnt.docx) (gerada pelo script
> [`scripts/generate_references_docx.py`](../scripts/generate_references_docx.py)).

1. ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023: informação e documentação — referências — elaboração**. Rio de Janeiro: ABNT, 2018. 68 p.
2. ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 14724: informação e documentação — trabalhos acadêmicos — apresentação**. Rio de Janeiro: ABNT, 2011. 113 p.
3. ZERO-TRUST-SYNDICATE. **Anti-cheat v8: detecção client-side das técnicas do laboratório**. [S.l.: s.n.], 2026. Disponível em: `rebuild/v8/ANTICHEAT-v8.md`. Acesso em: 1 set. 2026.
4. ZERO-TRUST-SYNDICATE. **Aimbot v8: guia de calibração e estudo de prevenção**. [S.l.: s.n.], 2026. Disponível em: `doc/Aimbot-e-prevencao.md`. Acesso em: 1 set. 2026.
5. VALVE CORPORATION. **Counter-Strike 1.6** [software]. Bellevue: Valve Corporation, 2003.
6. MICROSOFT. **ReadProcessMemory function (memoryapi.h)**. 2024. Disponível em: <https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory>. Acesso em: 1 set. 2026.
7. MICROSOFT. **VirtualQueryEx function (memoryapi.h)**. 2024. Disponível em: <https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualqueryex>. Acesso em: 1 set. 2026.
8. MICROSOFT. **CreateToolhelp32Snapshot function (tlhelp32.h)**. 2024. Disponível em: <https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-createtoolhelp32snapshot>. Acesso em: 1 set. 2026.
9. MICROSOFT. **OpenProcess function (processthreadsapi.h)**. 2024. Disponível em: <https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess>. Acesso em: 1 set. 2026.
10. PALLETS. **Flask documentation**. 2024. Disponível em: <https://flask.palletsprojects.com/>. Acesso em: 1 set. 2026.
11. TAILWIND LABS. **Tailwind CSS: utility-first CSS framework**. 2024. Disponível em: <https://tailwindcss.com/docs>. Acesso em: 1 set. 2026.
12. MERMAID. **Mermaid: diagramming and charting tool**. 2024. Disponível em: <https://mermaid.js.org/>. Acesso em: 1 set. 2026.
13. PYTHON SOFTWARE FOUNDATION. **sqlite3: SQLite databases**. Python 3.10.1 documentation. 2024. Disponível em: <https://docs.python.org/3/library/sqlite3.html>. Acesso em: 1 set. 2026.
14. H J CHEATS. **Cheat para Counter-Strike** [software analisado]. 2025. Disponível em: <https://dhjcheats.com/>. Acesso em: 1 set. 2026.
15. ALSCH092. **UltimateAntiCheat**: open source usermode anti-cheat system (C++, Windows). GitHub, [2023]. Disponível em: <https://github.com/AlSch092/UltimateAntiCheat>. Acesso em: 17 out. 2026.
16. VALVE CORPORATION. **Valve Anti-Cheat (VAC)**: sistema anti-cheat e banimentos de jogo. [S.l.]: Valve Corporation, 2003. Disponível em: <https://partner.steamgames.com/doc/features/anticheat>. Acesso em: 17 out. 2026.
