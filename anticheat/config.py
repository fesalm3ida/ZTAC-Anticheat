"""Configuração central do Anti-cheat.

Caminhos e constantes usados por toda a aplicação. Em produção (Windows) os
caminhos de sessão/DB são relativos à pasta do app; em WSL durante o
desenvolvimento usamos as mesmas pastas (data/ e a sessão em disco), o que
permite testar a GUI sem depender de um processo do Windows.
"""
from __future__ import annotations

import os
from pathlib import Path

# Raiz do projeto (pasta que contém app.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Pasta de dados (SQLite, sessões) — criada no boot se não existir
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Banco de dados de usuários e histórico de varreduras
DB_PATH = DATA_DIR / "anticheat.db"

# Pasta de sessões Flask (falha-behind seguro em WSL onde /tmp pode ser reincidido)
SESSION_DIR = DATA_DIR / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# Segredo da sessão. Em produção gere aleatoriamente; aqui deriva de um arquivo
# persistido para não invalidar a sessão a cada reinício.
SECRET_KEY_FILE = DATA_DIR / "secret.key"


def _load_secret_key() -> str:
    if SECRET_KEY_FILE.exists():
        return SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
    secret = os.urandom(32).hex()
    SECRET_KEY_FILE.write_text(secret, encoding="utf-8")
    return secret


SECRET_KEY = _load_secret_key()
SESSION_COOKIE_NAME = "anticheat_session"
PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8h

# Nomes de processo do CS 1.6 (alvo). A versão Revo roda como `cs.exe`; a
# Steam usa `hl.exe` / `cstrike.exe`. A varredura considera os três.
TARGET_PROCESS_NAMES = ("hl.exe", "cstrike.exe", "cs.exe")

# Nome do binário que representa o processo "limpo" durante o scan real.
# Usado apenas para mensagens; o scan decide pelo nome plus assinaturas.
GAME_NAME = "Counter-Strike 1.6"

# Endereço/porta do servidor Flask (bind)
HOST = os.environ.get("AC_HOST", "127.0.0.1")
PORT = int(os.environ.get("AC_PORT", "5050"))

# Tamanho do chunk de leitura de memória no scan de strings (bytes)
MEMORY_READ_CHUNK = 1 << 20  # 1 MiB
