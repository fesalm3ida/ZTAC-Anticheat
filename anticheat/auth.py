"""Autenticação — login/registro com sessão Flask e hash de senha.

Usa `werkzeug.security` (hash PBKDF2 por padrão) e a sessão assinada do Flask.
Depende do `g.scanner/db` configurado no app (ver `app.py`).
"""
from __future__ import annotations

from functools import wraps

from werkzeug.security import check_password_hash, generate_password_hash

from .db import Database


def register_user(db: Database, username: str, password: str):
    """Cria um usuário. Levanta ValueError se já existir."""
    username = username.strip()
    if not username or len(username) < 3:
        raise ValueError("Usuário deve ter pelo menos 3 caracteres.")
    if len(password) < 6:
        raise ValueError("Senha deve ter pelo menos 6 caracteres.")
    if db.get_user_by_name(username):
        raise ValueError("Usuário já existe.")
    return db.create_user(username, generate_password_hash(password))


def verify_user(db: Database, username: str, password: str):
    """Devolve o User se as credenciais forem válidas, senão None."""
    user = db.get_user_by_name(username.strip())
    if user and check_password_hash(user.password_hash, password):
        return user
    return None


def login_required(view):
    """Decorator: exige sessão autenticada (redireciona para /login na web)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        from flask import request, redirect, session, url_for
        if not session.get("user"):
            # API pede JSON; página pede redirecionamento
            if request.path.startswith("/api/"):
                from flask import jsonify
                return jsonify({"error": "Não autenticado"}), 401
            return redirect(url_for("login_page", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def api_login_required(view):
    """Decorator para endpoints JSON: devolve 401 se não autenticado."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        from flask import jsonify, session
        if not session.get("user"):
            return jsonify({"error": "Não autenticado"}), 401
        return view(*args, **kwargs)
    return wrapped
