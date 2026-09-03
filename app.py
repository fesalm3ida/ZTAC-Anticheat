"""Launcher do servidor do anti-cheat.

    python app.py            # abre em http://127.0.0.1:5050

Toda a lógica do app vive em `anticheat/` (web.py, api.py, scanner, …).
"""
from __future__ import annotations

from anticheat.web import main

if __name__ == "__main__":
    main()
