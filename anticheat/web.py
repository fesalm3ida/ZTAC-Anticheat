"""Fábrica do Flask app — mantida dentro do pacote para import limpo.

`app.py` é apenas o launcher. Caminhos de templates/static são resolvidos em
relação à raiz do projeto, não ao pacote.
"""
from __future__ import annotations

import os

from flask import Flask, render_template

from .api import api as api_blueprint
from .auth import login_required
from .config import BASE_DIR, DB_PATH, HOST, PORT, SECRET_KEY, SESSION_COOKIE_NAME
from .db import Database
from .scanner import create_scanner


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config.update(
        SECRET_KEY=SECRET_KEY,
        SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
        SESSION_PERMANENT=True,
    )

    db = Database(str(DB_PATH))
    scanner = create_scanner()

    # Deixa explícito no console qual backend/modo foi selecionado. O scan real
    # (WindowsScanner) só é usado quando o servidor roda no Windows; em outro SO
    # (WSL/Linux) cai no SimulatedScanner (modo demo), que fabrica o relatório.
    print(f"[anti-cheat] backend={type(scanner).__name__} mode={scanner.mode!r} "
          f"(capture o processo do jogo no mesmo host)")

    app.config["DB"] = db
    app.config["SCANNER"] = scanner

    app.register_blueprint(api_blueprint)

    # ------------------------------------------------------------------
    # Páginas
    # ------------------------------------------------------------------
    @app.route("/")
    @login_required
    def index():
        return render_template("dashboard.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/register")
    def register_page():
        return render_template("register.html")

    return app


app = create_app()


def main():
    # debug desligado por padrão; defina AC_DEBUG=1 para ativar em dev
    debug = os.environ.get("AC_DEBUG", "") == "1"
    app.run(host=HOST, port=PORT, debug=debug)


if __name__ == "__main__":
    main()
