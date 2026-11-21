## O que foi construído

O anti-cheat web foi construído sobre uma arquitetura em três camadas que
separa, deliberadamente, a interface, a orquestração e a detecção. O
**frontend**, servido pelo próprio Flask, concentra a apresentação e a
interação do usuário; o **backend** reúne as regras de negócio, a autenticação,
a persistência e a coordenação da varredura; e o **scanner** concentra a lógica
de leitura e de análise da memória do processo do jogo. Essa separação garante
que a mecânica de detecção possa evoluir — e ser testada — independentemente da
interface, e é também o que torna possível a coexistência de dois modos de
operação, conforme descrito adiante.

### Detecção em três estágios

O núcleo da solução é composto por três estágios de detecção, herdados do
anti-cheat v8 e executados em sequência, cada um produzindo evidências
independentes:

- **Estágio A — Módulos:** enumera as bibliotecas dinâmicas carregadas no
  processo e sinaliza as DLLs injetadas, as que estão fora da lista branca
  (*whitelist*), as carregadas a partir de diretórios temporários (`temp`) e
  aquelas cujo nome apresenta aparência hexadecimal aleatória.
- **Estágio B — Detours:** verifica os *exports* do `opengl32.dll`, comparando
  os bytes presentes na memória com os bytes da imagem em disco. A presença de
  `mem[0] == 0xE9` caracteriza um *detour* inline, enquanto a divergência entre
  disco e memória indica *patch* ou modificação do código original.
- **Estágio C — Artefatos:** inspeciona artefatos em disco, como os arquivos de
  log em `C:\Temp`, e varre a memória do processo em busca de strings
  características dos cheats.

### Diagrama de componentes

```mermaid
flowchart TB
    classDef ui    fill:#1e293b,stroke:#818cf8,stroke-width:2px,color:#e2e8f0
    classDef core  fill:#1e293b,stroke:#22d3ee,stroke-width:2px,color:#e2e8f0
    classDef scan  fill:#1e293b,stroke:#fb7185,stroke-width:2px,color:#e2e8f0
    classDef stage fill:#0b1220,stroke:#fbbf24,stroke-width:1.5px,color:#fde68a
    classDef ext   fill:#0b1220,stroke:#94a3b8,stroke-width:1.5px,color:#cbd5e1,stroke-dasharray:5 4

    USR(["Usuário"]):::ui

    subgraph L1["1 · APRESENTAÇÃO — browser"]
        direction LR
        UI["templates/<br/>login · register · dashboard · base"]:::ui
        JS["static/<br/>app.js · auth.js"]:::ui
        UI --> JS
    end

    subgraph L2["2 · APLICAÇÃO — Flask"]
        direction LR
        WEB["web.py<br/>rotas de página"]:::core
        API["api.py<br/>REST /api/*"]:::core
        AUTH["auth.py<br/>sessão + hash"]:::core
        DB[("db.py<br/>SQLite")]:::core
        CFG["config.py"]:::core
        WEB --> API
        API --> AUTH
        API --> DB
        CFG -.-> API
    end

    subgraph L3["3 · DETECÇÃO — scanner"]
        direction LR
        BASE["base.py<br/>interface + ScanReport"]:::scan
        SIG["signatures.py"]:::scan
        PE["pe_parser.py<br/>PE32 / PE64"]:::scan
        WS["windows_scanner.py<br/>ctypes → kernel32"]:::scan
        SS["simulated_scanner.py<br/>demo"]:::scan
        BASE --> SIG
        BASE -.->|"Windows"| WS
        BASE -.->|"WSL / Linux"| SS
        WS --> PE
        subgraph EST["estágios de detecção"]
            direction LR
            A1["A · Módulos"]:::stage
            B1["B · Detours"]:::stage
            C1["C · Artefatos"]:::stage
        end
        WS --> EST
    end

    USR ==> UI
    UI ==>|"HTTP · JSON"| WEB
    JS ==>|"Fetch API"| API
    API ==>|"create_scanner()"| BASE
    WS ==>|"ReadProcessMemory · VirtualQueryEx"| GAME[("Processo do jogo<br/>hl.exe / cstrike.exe")]:::ext
    SS ==> DEMO[("Dados sintéticos")]:::ext
    EST ==>|"ScanReport"| DB

    style L1 fill:#0f172a,stroke:#818cf8,stroke-width:1.5px,color:#c7d2fe
    style L2 fill:#0f172a,stroke:#22d3ee,stroke-width:1.5px,color:#a5f3fc
    style L3 fill:#0f172a,stroke:#fb7185,stroke-width:1.5px,color:#fecdd3
    style EST fill:#111827,stroke:#fbbf24,stroke-width:1.5px,color:#fde68a
```

### Estrutura de módulos

A organização do código acompanha diretamente a separação de responsabilidades
da arquitetura:

| Camada | Local | Componentes |
|---|---|---|
| **Backend** | `anticheat/` | `web.py` (aplicação), `api.py` (API REST), `auth.py` (sessão + hash), `db.py` (SQLite) e `config.py` (configurações). |
| **Scanner** | `anticheat/scanner/` | `base.py` (interface e modelo do relatório), `signatures.py` (assinaturas), `pe_parser.py` (parser PE32/PE64), `windows_scanner.py` (varredura real via `ctypes` → `kernel32`) e `simulated_scanner.py` (modo demonstração). |
| **Frontend** | `templates/` e `static/` | `templates/` (`login`, `register`, `dashboard`, `base`) e `static/` (`app.js`, `auth.js`). |

Por fim, o sistema realiza **seleção automática de backend** conforme o
ambiente: no **Windows**, utiliza a varredura real de memória; em ambientes
**WSL/Linux**, recorre ao modo de demonstração, o que permite desenvolver e
testar toda a interface sem a necessidade de um processo do jogo em execução.
