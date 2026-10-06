import logging
import os
import sqlite3
import threading
import time

import bcrypt

from app import config

logger = logging.getLogger(__name__)

ROLES = ("ADMIN", "ENGINEER", "VIEWER")

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL,
    created_at     REAL NOT NULL
);
"""


class UserError(Exception):
    pass


def _connect():
    directory = os.path.dirname(config.USERS_DB_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(config.USERS_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.executescript(_SCHEMA)
        count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if count == 0:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (
                    config.ADMIN_USERNAME,
                    hash_password(config.ADMIN_PASSWORD),
                    "ADMIN",
                    time.time(),
                ),
            )
            logger.warning(
                "Seeded initial ADMIN user %r from ADMIN_USERNAME/ADMIN_PASSWORD",
                config.ADMIN_USERNAME,
            )
        else:
            logger.info("Users table already populated (%d users); not seeding", count)


def get_user(username: str):
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT username, password_hash, role, created_at FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return dict(row) if row else None


def list_users():
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT username, role, created_at FROM users ORDER BY created_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def create_user(username: str, password: str, role: str) -> dict:
    username = (username or "").strip()
    if len(username) < 3:
        raise UserError("Username must be at least 3 characters.")
    if len(password or "") < 8:
        raise UserError("Password must be at least 8 characters.")
    if role not in ROLES:
        raise UserError(f"Role must be one of {', '.join(ROLES)}.")

    with _lock, _connect() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        if exists:
            raise UserError(f"User {username!r} already exists.")
        created = time.time()
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), role, created),
        )
    logger.warning("Created user %r with role %s", username, role)
    return {"username": username, "role": role, "created_at": created}


def set_role(username: str, role: str) -> dict:
    if role not in ROLES:
        raise UserError(f"Role must be one of {', '.join(ROLES)}.")

    with _lock, _connect() as conn:
        row = conn.execute("SELECT role FROM users WHERE username = ?", (username,)).fetchone()
        if row is None:
            raise UserError(f"User {username!r} does not exist.")
        if row["role"] == "ADMIN" and role != "ADMIN":
            remaining = conn.execute(
                "SELECT COUNT(*) AS n FROM users WHERE role = 'ADMIN' AND username != ?",
                (username,),
            ).fetchone()["n"]
            if remaining == 0:
                raise UserError("Refusing to remove the last ADMIN.")
        conn.execute("UPDATE users SET role = ? WHERE username = ?", (role, username))
    logger.warning("Changed role of %r to %s", username, role)
    return {"username": username, "role": role}
