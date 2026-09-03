# Implantação e configuração do anti-cheat

Guia prático de instalação, execução e ajustes de configuração do anti-cheat
web (Flask + Tailwind). Para a visão geral da arquitetura, veja
[architecture.md](architecture.md).

---

## 1. Pré-requisitos

- **Python 3.9+** (testado com 3.10).
- Dependências (apenas Flask — as demais são da stdlib): ver `requirements.txt`.
- **Para o scan real:** um **Windows** com o CS 1.6 (`hl.exe` / `cstrike.exe`)
  rodando. O servidor precisa de privilégio para abrir o processo do jogo.

```
Flask>=3.0
```

---

## 2. Instalação

```bash
# 1. clone / copie a pasta do projeto
cd anticheat

# 2. (opcional) crie um venv
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. instale as dependências
python -m pip install -r requirements.txt
```

> No Windows use `python` (não `python3`); no WSL/Linux use `python3`.

---

## 3. Execução

### 3.1 Windows — scan real (junto do jogo)

```bat
cd C:\caminho\anticheat
python -m pip install -r requirements.txt
python app.py          ;  ou: run.bat
```

Abra **http://127.0.0.1:5050**, crie uma conta e clique em **Iniciar varredura**.

**Privilégios:** para ler a memória de `hl.exe`, o processo do servidor precisa
de permissão equivalente à do jogo. Se o dashboard mostrar
*"Não foi possível abrir o processo"*, execute o terminal/`run.bat` **como
administrador** (`Run as administrator`).

### 3.2 WSL / Linux — modo demo (sem processo do jogo)

```bash
cd /home/fealmeida/deepseek-ai/workspace/anticheat
python3 -m pip install -r requirements.txt
python3 app.py
```

Neste cenário o backend é o **SimulatedScanner**: o botão
**"Simular processo limpo (demo)"** alterna entre `HACKEADO` (cheat v8 injetado)
e `LIMPO`, para você validar a GUI e o pipeline.

---

## 4. Configuração

### 4.1 Variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `AC_HOST` | `127.0.0.1` | Endereço de bind do Flask. Use `0.0.0.0` para aceitar conexões de rede. |
| `AC_PORT` | `5050` | Porta do servidor. |
| `AC_DEBUG` | *(vazio)* | `1` ativa o modo debug do Flask (recarga automática, tracebacks). |
| `AC_FORCE_DEMO` | *(vazio)* | `1` força o backend demo **mesmo no Windows** (útil para testar a UI sem o jogo). |

Exemplo:

```bash
# Windows
set AC_PORT=8080
set AC_DEBUG=1
python app.py

# WSL/Linux
AC_HOST=0.0.0.0 AC_PORT=8080 AC_FORCE_DEMO=1 python3 app.py
```

### 4.2 Configuração em `anticheat/config.py`

| Item | Default | Descrição |
|---|---|---|
| `DB_PATH` | `data/anticheat.db` | Banco SQLite (usuários + histórico). |
| `SECRET_KEY` | derivada de `data/secret.key` | Assina a sessão. Gerada na 1ª execução e persistida para não invalidar sessões. |
| `SESSION_COOKIE_NAME` | `anticheat_session` | Nome do cookie de sessão. |
| `PERMANENT_SESSION_LIFETIME` | 8 h | Validade da sessão. |
| `TARGET_PROCESS_NAMES` | `("hl.exe","cstrike.exe")` | Processos alvo do jogo. |
| `GAME_NAME` | `Counter-Strike 1.6` | Nome exibido. |
| `HOST` / `PORT` | `127.0.0.1` / `5050` | Bind do servidor (sobrescritos por AC_HOST/AC_PORT). |
| `MEMORY_READ_CHUNK` | 1 MiB | Tamanho do bloco de leitura no scan de strings. |

> ⚠️ Em produção, troque `SECRET_KEY` por um valor fixo/aleatório seu (ou
> confie no arquivo `data/secret.key`). Não exponha o servidor à internet sem
> HTTPS e autenticação.

### 4.3 Assinaturas de detecção — `anticheat/scanner/signatures.py`

Centralize aqui o que o anti-cheat procura (herdado do v8):

| Constante | O que controla |
|---|---|
| `KNOWN_CHEAT_MODULES` | Lista negra de módulos (ex.: `hook_v8.dll`, `wallhack.dll`, `aimbot_v8.dll`, `main_v8.dll`). |
| `TRUSTED_PATH_MARKERS` | Substrings de caminho tratadas como "raiz confiável" (`\steam\`, `\system32\`, …). |
| `OPENGL_HOOK_TARGETS` | Exports do `opengl32.dll` que são alvo do wallhack v8. |
| `INLINE_HOOK_BYTE` | Byte que denota detour inline (`0xE9`). |
| `EXPORT_BYTES_TO_COMPARE` | Nº de bytes comparados entre disco e memória (16). |
| `KNOWN_MEMORY_SIGNATURES` | Strings procuradas na memória (`AIMBOT PRONTO`, `ForceWallhack`, …). |
| `KNOWN_LOG_FILES` | Arquivos de log que denunciam o cheat (`C:\Temp\*_Debug.txt`). |
| `SEVERITY_WEIGHT` | Peso de cada severidade no cálculo do score. |

Para adicionar um padrão novo, basta acrescentar à constante correspondente.

---

## 5. Estrutura de dados

- **`data/anticheat.db`** — SQLite:
  - `users(id, username, password_hash, created_at)`
  - `scans(id, user_id, created_at, verdict, score, simulated, process_name,
    process_pid, report_json)`
- **`data/secret.key`** — chave da sessão (criada na 1ª execução).
- **Sessão** — cookie assinado no navegador (sem estado no servidor).

> O banco **se auto-cura**: o schema é garantido (idempotente) antes de cada
> operação. Se o arquivo for removido/esvaziado ou estiver corrompido enquanto
> o servidor roda, ele é recriado automaticamente (e um arquivo corrompido é
> preservado como `anticheat.db.corrupt`). As contas de usuário são perdidas
> nesses casos — a app passa a funcionar novamente, sem `no such table`.

---

## 6. Teste rápido (smoke) após instalar

```bash
cd anticheat
python3 -c "
from anticheat.web import create_app
app = create_app()
c = app.test_client()
print('register:', c.post('/api/register', json={'username':'u','password':'secret123'}).status_code)
print('login:', c.post('/api/login', json={'username':'u','password':'secret123'}).status_code)
print('mode:', c.get('/api/processes').get_json()['mode'])
print('scan:', c.post('/api/scan', json={}).get_json()['verdict'])
"
```

Esperado: `register: 201`, `login: 200`, `mode: demo` (no WSL),
`scan: hackeado`.

---

## 7. Solução de problemas

| Sintoma | Causa | Solução |
|---|---|---|
| `Não foi possível abrir o processo` | Sem privilégio para `OpenProcess` | Rode como administrador. |
| `Nenhum processo do jogo` | `hl.exe`/`cstrike.exe` não está rodando | Inicie o jogo (offline contra bots). |
| Estágio A acusa DLL do seu AV | Falso positivo de whitelist | Adicione o caminho do AV a `TRUSTED_PATH_MARKERS`. |
| `hackeado` com score 100 no WSL | Backend demo padrão (cheat simulado) | Use "Simular processo limpo (demo)" para ver LIMPO. |
| Sessão expirando rápido | Cookie de sessão | Reduza `PERMANENT_SESSION_LIFETIME`/`AC_*` — ou aumente a validade. |
| Porta ocupada | `5050` em uso | Defina `AC_PORT`. |

---

## 8. Produção (opcional)

O `app.run()` do Flask é um servidor de **desenvolvimento**. Para produção,
use um WSGI server (ex.: `waitress` no Windows) atrás de um proxy:

```bash
pip install waitress
waitress-serve --host 127.0.0.1 --port 5050 anticheat.web:app
```

Mantenha o bind local (`127.0.0.1`) e, se for expor, use HTTPS e um proxy
reverso. **Escopo acadêmico/laboratório:** mantenha o teste offline contra bots
e evite rodar o scanner em partidas online protegidas por VAC.
