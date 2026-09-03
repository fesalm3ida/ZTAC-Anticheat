"""Persistência — SQLite (usuários + histórico de varreduras).

Camadas finas sobre `sqlite3` da stdlib. O schema é garantido de forma
**idempotente antes de cada operação** (`CREATE TABLE IF NOT EXISTS`), de modo
que o banco se "auto-cura" mesmo que o arquivo seja recriado vazio ou removido
enquanto o servidor está no ar — eliminando `no such table`.

Conexões são criadas por operação (ninguém é compartilhado entre threads).
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    created_at    TEXT NOT NULL,
    verdict       TEXT,
    score         INTEGER,
    simulated     INTEGER,
    process_name  TEXT,
    process_pid   INTEGER,
    report_json   TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    created_at: str


class Database:
    """Acesso a dados com conexões por operação (thread-safety simples)."""

    def __init__(self, path: str = str(DB_PATH)) -> None:
        self.path = path
        self._init_schema()

    # ------------------------------------------------------------------
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Cria o schema se ausente. Idempotente e seguro p/ arquivo vazio."""
        try:
            conn = self._conn()
            try:
                conn.executescript(_SCHEMA)
                conn.commit()
            finally:
                conn.close()
        except sqlite3.DatabaseError:
            # Arquivo corrompido / não é um banco válido: preserva o original
            # e recria um banco limpo com o schema.
            self._recreate_from_corrupt()

    def _recreate_from_corrupt(self) -> None:
        backup = self.path + ".corrupt"
        try:
            if os.path.exists(self.path):
                os.replace(self.path, backup)
        except OSError:
            pass
        conn = sqlite3.connect(self.path)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Garante as tabelas presentes, mesmo se o arquivo foi esvaziado.

        Barato: checa `users` e só executa o schema (IF NOT EXISTS) se faltar.
        """
        conn = self._conn()
        try:
            try:
                conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
            except sqlite3.OperationalError:
                # tabela ausente (arquivo recriado/esvaziado) → (re)cria
                conn.executescript(_SCHEMA)
                conn.commit()
            except sqlite3.DatabaseError:
                # arquivo inválido → recria do zero
                self._recreate_from_corrupt()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # usuários
    # ------------------------------------------------------------------
    def create_user(self, username: str, password_hash: str) -> User:
        self._ensure_schema()
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
                (username, password_hash, datetime.now().isoformat(timespec="seconds")),
            )
            conn.commit()
            return self.get_user_by_id(cur.lastrowid)
        finally:
            conn.close()

    def get_user_by_name(self, username: str) -> User | None:
        self._ensure_schema()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return self._row_to_user(row)
        finally:
            conn.close()

    def get_user_by_id(self, user_id: int) -> User | None:
        self._ensure_schema()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return self._row_to_user(row)
        finally:
            conn.close()

    @staticmethod
    def _row_to_user(row: sqlite3.Row | None) -> User | None:
        if not row:
            return None
        return User(id=row["id"], username=row["username"],
                    password_hash=row["password_hash"],
                    created_at=row["created_at"])

    # ------------------------------------------------------------------
    # histórico de varreduras
    # ------------------------------------------------------------------
    def save_scan(self, user_id: int, report: dict) -> int:
        self._ensure_schema()
        conn = self._conn()
        try:
            import json
            cur = conn.execute(
                "INSERT INTO scans(user_id, created_at, verdict, score, simulated,"
                " process_name, process_pid, report_json) VALUES(?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    report.get("timestamp", ""),
                    report.get("verdict", ""),
                    report.get("score", 0),
                    1 if report.get("simulated") else 0,
                    report.get("process", {}).get("name", ""),
                    report.get("process", {}).get("pid", 0),
                    json.dumps(report, ensure_ascii=False),
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_scans(self, user_id: int, limit: int = 20) -> list[dict]:
        self._ensure_schema()
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM scans WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_scan(self, scan_id: int, user_id: int) -> dict | None:
        self._ensure_schema()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM scans WHERE id = ? AND user_id = ?",
                (scan_id, user_id)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
