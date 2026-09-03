"""Blueprint de API — endpoints JSON consumidos pelo frontend.

Rotas:
  POST /api/register        cria usuário
  POST /api/login           autentica
  POST /api/logout          encerra sessão
  GET  /api/me              estado da sessão
  GET  /api/processes       lista processos do jogo (candidatos)
  POST /api/scan            dispara varredura (body: {"pid": int|None, "clean": bool})
  GET  /api/reports         histórico de varreduras do usuário
  GET  /api/reports/<id>    um relatório específico
"""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, session

from .auth import api_login_required, register_user, verify_user

api = Blueprint("api", __name__, url_prefix="/api")


def _db():
    return current_app.config["DB"]


def _scanner():
    return current_app.config["SCANNER"]


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
@api.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    try:
        register_user(_db(), username, password)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    user = verify_user(_db(), username, password)
    session["user"] = {"id": user.id, "username": user.username}
    session.permanent = True
    return jsonify({"ok": True, "username": user.username}), 201


@api.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    user = verify_user(_db(), data.get("username", ""), data.get("password", ""))
    if not user:
        return jsonify({"error": "Credenciais inválidas"}), 401
    session["user"] = {"id": user.id, "username": user.username}
    session.permanent = True
    return jsonify({"ok": True, "username": user.username})


@api.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@api.route("/me", methods=["GET"])
def me():
    user = session.get("user")
    if not user:
        return jsonify({"authenticated": False}), 200
    return jsonify({"authenticated": True, "user": user})


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------
@api.route("/processes", methods=["GET"])
@api_login_required
def processes():
    scanner = _scanner()
    return jsonify({"mode": scanner.mode, "processes": scanner.list_processes()})


@api.route("/scan", methods=["POST"])
@api_login_required
def scan():
    data = request.get_json(silent=True) or {}
    pid = data.get("pid") or None

    scanner = _scanner()
    # No modo demo permite simular cenários para testar a UI:
    #   clean=True      → veredito LIMPO
    #   no_process=True → aviso "processo do CS não encontrado"
    if scanner.mode == "demo":
        from .scanner.simulated_scanner import SimulatedScanner
        scanner = SimulatedScanner(
            anomalous=not data.get("clean"),
            no_process=bool(data.get("no_process")),
        )

    report = scanner.scan(pid)
    report_dict = report.to_dict()

    user = session["user"]
    # Avisos de "processo não encontrado" não são varreduras reais — não vão
    # para o histórico, mas ainda são devolvidos para a UI exibir o aviso.
    if report_dict.get("verdict") == "sem_processo":
        report_dict["id"] = None
    else:
        report_dict["id"] = _db().save_scan(user["id"], report_dict)
    return jsonify(report_dict)


# ---------------------------------------------------------------------------
# Histórico
# ---------------------------------------------------------------------------
@api.route("/reports", methods=["GET"])
@api_login_required
def reports():
    return jsonify({"reports": _db().get_scans(session["user"]["id"])})


@api.route("/reports/<int:scan_id>", methods=["GET"])
@api_login_required
def report_detail(scan_id: int):
    import json
    row = _db().get_scan(scan_id, session["user"]["id"])
    if not row:
        return jsonify({"error": "Relatório não encontrado"}), 404
    row["report"] = json.loads(row.pop("report_json"))
    return jsonify(row)
