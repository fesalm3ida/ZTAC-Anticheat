# Anti-cheat web — Flask + Tailwind

Console de detecção de cheats com **interface gráfica web**, **login**,
**backend Flask** e **frontend Tailwind**. O scanner identifica anomalias na
memória do processo do jogo (CS 1.6) em três estágios, herdando as assinaturas
do anti-cheat v8 do projeto `Zero-Trust-Syndicate`:

| Estágio | O que detecta |
|---|---|
| **A — Módulos** | DLLs injetadas fora do diretório do jogo/sistema (lista negra: `hook_v8.dll`, `wallhack.dll`, `aimbot_v8.dll`, `main_v8.dll`, …), diretório `temp`, nome "hex aleatório". |
| **B — Detours** | Hooks inline (`E9 + rel32`) e divergências disco×memória nos exports do `opengl32.dll` (`wglSwapBuffers`, `glBegin`, `glEnd`, `glEnable`, `glDisable`, `glDepthFunc`, `glStencilFunc`, …). |
| **C — Artefatos** | Logs em `C:\Temp\*_Debug.txt` e strings na memória (`AIMBOT PRONTO`, `ForceWallhack`, `hk_wglSwapBuffers`, `gEngfuncs`, …). |

> 📚 **Documentação**
> - [Diagrama de arquitetura (Mermaid)](docs/architecture.md) ·
>   [Diagrama interativo no navegador](docs/architecture.html)
> - [Implantação e configuração](docs/deployment.md)

---

## 1. Arquitetura

```
anticheat/
├── app.py                     # launcher: python app.py
├── requirements.txt
├── run.bat                    # launcher Windows (.bat)
├── anticheat/
│   ├── web.py                 # fábrica do Flask app
│   ├── api.py                 # Blueprint REST (/api/*)
│   ├── auth.py                # login/registro, sessão, hash
│   ├── db.py                  # SQLite (usuários + histórico de scans)
│   ├── config.py              # caminhos e constantes
│   └── scanner/
│       ├── base.py            # interface e modelo ScanReport/Finding
│       ├── signatures.py      # assinaturas herdadas do v8
│       ├── windows_scanner.py # scan REAL (ctypes → kernel32/ntdll)
│       ├── simulated_scanner.py # demo (desenvolvimento/UI)
│       └── pe_parser.py       # parser de PE (exports, RVA→offset)
├── templates/                 # Jinja + Tailwind (CDN)
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
├── static/
│   ├── auth.js
│   └── app.js
└── data/                      # SQLite + chave de sessão (gerados)
```

### Seleção automática do backend

`scanner/__init__.py` escolhe:

- **Windows** (`os.name == "nt"`) → `WindowsScanner` (scan real de memória).
- **Qualquer outro SO** (ex.: WSL, para desenvolver a UI) → `SimulatedScanner`
  (dados sintéticos no mesmo formato).

Force o modo demo no Windows com a variável `AC_FORCE_DEMO=1`.

---

## 2. Onde rodar

**O scan de memória só funciona de verdade no Windows** (usa
`ReadProcessMemory`/`VirtualQueryEx`/`CreateToolhelp32Snapshot` via `ctypes`).

### 2.1 Windows (scan real, junto do jogo)

```bat
cd C:\caminho\anticheat
python -m pip install -r requirements.txt
python app.py            ; ou run.bat
```

Abra **http://127.0.0.1:5050**, crie uma conta, clique em **Iniciar varredura**.

> **Privilégios**: para ler a memória de outro processo (`hl.exe`), o agente
> precisa de permissão equivalente à do jogo. Rode o servidor **como
> administrador** se o `OpenProcess` falhar (o dashboard mostra esse erro).
> Exceção legítima no Estágio A: DLLs de antivírus/EDR injetadas no processo —
> identifique e ignore as do seu AV.

### 2.2 WSL / Linux (demo, sem processo do jogo)

Útil para desenvolver/testar a GUI e o pipeline de detecção:

```bash
cd /caminho/do/anticheat
python3 -m pip install -r requirements.txt
python3 app.py
```

Aqui o backend é o `SimulatedScanner`: o item **"Simular processo limpo (demo)"**
alterna entre o veredito `HACKEADO` (cheat v8 injetado) e `LIMPO`.

---

## 3. Uso

1. **Criar conta** em `/register` e entrar.
2. Escolher o processo alvo (o scanner detecta `hl.exe`/`cstrike.exe`).
3. **Iniciar varredura**.
4. Ver o veredito (LIMPO / SUSPEITO / HACKEADO), o score de ameaça e os
   achados agrupados por estágio.
5. Consultar o **Histórico** no fim da página.

### Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/register` | cria usuário |
| POST | `/api/login` | autentica |
| POST | `/api/logout` | encerra sessão |
| GET  | `/api/me` | estado da sessão |
| GET  | `/api/processes` | processos do jogo (`mode`: `real`/`demo`) |
| POST | `/api/scan` | dispara scan (`{"pid": int\|null}`). No demo aceita `{"clean": true}` (veredito LIMPO) e `{"no_process": true}` (aviso processo não encontrado). Se não houver processo do CS ativo, retorna `verdict` `sem_processo` + `warning` (não gravado no histórico). |
| GET  | `/api/reports` | histórico do usuário |
| GET  | `/api/reports/<id>` | um relatório |

---

## 4. Detecção em detalhe

- **Estágio A** usa `CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|SNAPMODULE32)`,
  lista negra explícita + whitelist por caminho (games dir, `system32`,
  `syswow64`, `Steam`) + heurística `temp`/hex-aleatório.
- **Estágio B** parseia o `opengl32.dll` do disco (PE32/PE32+) e compara os
  primeiros 16 bytes de cada export com os bytes lidos na memória
  (`module_base + rva`). `mem[0] == 0xE9` → detour inline (crítico);
  divergência de bytes → suspeita/patch.
- **Estágio C** verifica os logs em `C:\Temp` e varre as regiões de memória
  legíveis com `VirtualQueryEx` + `ReadProcessMemory` procurando as assinaturas
  (case-insensitive).

---

## 5. Notas e limites

- **Não roda scans reais no WSL**: o backend simulado é só para UI/desenvolvimento.
- **Falsos positivos (B)**: relocações PE podem alterar bytes entre disco e
  memória; o veredito mais forte é `mem[0] == 0xE9`. Divergência isolada é
  sinal de "verificar".
- Scan é **externo** (somente leitura, não injeta nada).
- Ambiente de laboratório recomendado (offline contra bots) para não colidir
  com anti-cheats online.

---

## 6. Extensões naturais

- Plugin server-side (AMX Mod X) com heurísticas de snap/linha de visão.
- Assinaturas adicionais/atualizáveis via YAML/JSON.
- Correlação dos logs do cheat com dados do servidor.
