"""
인증 서비스 — SQLite 기반 사용자/세션 관리
"""
import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

import config

_db_path = config.AUTH_DB_PATH


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """테이블 생성 (서버 시작 시 호출)"""
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL
        );
    """)
    conn.close()


# ── 비밀번호 ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations=260_000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, dk_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations=260_000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


# ── 사용자 CRUD ───────────────────────────────────────────

def create_user(username: str, password: str, role: str = "admin") -> dict:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return _user_dict(row)
    finally:
        conn.close()


def authenticate(username: str, password: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row and verify_password(password, row["password_hash"]):
            return _user_dict(row)
        return None
    finally:
        conn.close()


def list_users() -> list:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_user(user_id: int, username: str = None, password: str = None, role: str = None) -> Optional[dict]:
    conn = _get_conn()
    try:
        parts, params = [], []
        if username is not None:
            parts.append("username = ?"); params.append(username)
        if password is not None:
            parts.append("password_hash = ?"); params.append(hash_password(password))
        if role is not None:
            parts.append("role = ?"); params.append(role)
        if not parts:
            return None
        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(parts)} WHERE id = ?", params)
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _user_dict(row) if row else None
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _user_dict(row) -> dict:
    return {"id": row["id"], "username": row["username"], "role": row["role"], "created_at": row["created_at"]}


# ── 세션 ──────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(hours=config.SESSION_EXPIRY_HOURS)
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires.isoformat()),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_session_user(token: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT u.id, u.username, u.role, u.created_at
            FROM sessions s JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > datetime('now')
        """, (token,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token: str):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()
