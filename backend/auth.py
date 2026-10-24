"""Accounts, passwords, and sessions for Campus Customs (Problem 4).

Passwords
    PBKDF2-HMAC-SHA256, 120,000 iterations, stored as
    "pbkdf2_sha256$<salt>$<hex digest>". This matches the seeded test user
    exactly: the salt is a random string used as its UTF-8 bytes, and the
    digest is stored as hex. Login reads the salt back out of the stored
    value, re-hashes what the user typed with it, and compares in constant time.

Sessions
    Logging in creates a random session token. The browser keeps the token;
    the database keeps only a SHA-256 hash of it, so a leaked database cannot
    be used to log in as anyone.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_HEX_CHARS = 16          # 8 random bytes written as 16 hex characters
SESSION_DAYS = 7
MIN_PASSWORD_LENGTH = 8
MAX_FAILED_LOGINS = 5        # per email, per window
FAILED_LOGIN_WINDOW_S = 15 * 60

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------- passwords

def hash_password(password: str, salt: str | None = None) -> str:
    """Hash a password. A new random salt is made for new passwords only."""
    if salt is None:
        salt = secrets.token_hex(SALT_HEX_CHARS // 2)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    ).hex()
    return f"{ALGORITHM}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Re-hash the typed password with the stored salt and compare safely."""
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    candidate = hash_password(password, salt).split("$")[2]
    return hmac.compare_digest(candidate, expected)


# A real hash used when the email doesn't exist, so a wrong email takes as long
# to reject as a wrong password (no timing hint about which accounts exist).
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ----------------------------------------------------------------- sessions

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_auth_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()


def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_token_hash(token), user_id, expires.strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    return token


def user_for_token(conn: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT u.id, u.first_name, u.last_name, u.email
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > datetime('now')
        """,
        (_token_hash(token),),
    ).fetchone()


# ------------------------------------------------- brute-force protection

_failed: dict[str, deque[float]] = defaultdict(deque)


def _too_many_failures(email: str) -> bool:
    attempts = _failed[email]
    cutoff = time.monotonic() - FAILED_LOGIN_WINDOW_S
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return len(attempts) >= MAX_FAILED_LOGINS


# --------------------------------------------------------------------- API

class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class PublicUser(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: PublicUser


def _public(row: sqlite3.Row) -> PublicUser:
    return PublicUser(
        id=row["id"],
        first_name=row["first_name"] or "",
        last_name=row["last_name"] or "",
        email=row["email"],
    )


def build_router(connect: Callable[[], sqlite3.Connection]) -> tuple[APIRouter, Callable, Callable]:
    """Make the /api/auth routes plus two dependencies: one that requires a
    logged-in user, and one that returns the user or None."""
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    def bearer_token(authorization: str | None = Header(default=None)) -> str | None:
        if authorization and authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        return None

    def current_user(token: str | None = Depends(bearer_token)) -> PublicUser:
        if not token:
            raise HTTPException(status_code=401, detail="Please log in.")
        with connect() as conn:
            row = user_for_token(conn, token)
        if row is None:
            raise HTTPException(status_code=401, detail="Your session has ended. Please log in again.")
        return _public(row)

    def optional_user(token: str | None = Depends(bearer_token)) -> PublicUser | None:
        if not token:
            return None
        with connect() as conn:
            row = user_for_token(conn, token)
        return _public(row) if row else None

    @router.post("/signup", response_model=AuthResponse)
    def signup(req: SignupRequest) -> AuthResponse:
        first, last = req.first_name.strip(), req.last_name.strip()
        email = req.email.strip().lower()
        if not first or not last:
            raise HTTPException(400, "Please enter your first and last name.")
        if not EMAIL_RE.match(email):
            raise HTTPException(400, "Please enter a valid email address.")
        if len(req.password) < MIN_PASSWORD_LENGTH:
            raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

        with connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM users WHERE lower(email) = ?", (email,)
            ).fetchone()
            if exists:
                raise HTTPException(409, "An account with that email already exists. Try logging in.")
            cur = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (f"{first} {last}", email, hash_password(req.password), first, last),
            )
            user_id = cur.lastrowid
            conn.commit()
            token = create_session(conn, user_id)
        return AuthResponse(
            token=token, user=PublicUser(id=user_id, first_name=first, last_name=last, email=email)
        )

    @router.post("/login", response_model=AuthResponse)
    def login(req: LoginRequest) -> AuthResponse:
        email = req.email.strip().lower()
        if _too_many_failures(email):
            raise HTTPException(429, "Too many attempts. Please wait 15 minutes and try again.")

        with connect() as conn:
            row = conn.execute(
                "SELECT id, first_name, last_name, email, password_hash FROM users WHERE lower(email) = ?",
                (email,),
            ).fetchone()
            ok = verify_password(req.password, row["password_hash"] if row else _DUMMY_HASH)
            if not row or not ok:
                _failed[email].append(time.monotonic())
                # Same message either way, so nobody can probe which emails have accounts.
                raise HTTPException(401, "Email or password is incorrect.")
            _failed.pop(email, None)
            token = create_session(conn, row["id"])
        return AuthResponse(token=token, user=_public(row))

    @router.get("/me", response_model=PublicUser)
    def me(user: PublicUser = Depends(current_user)) -> PublicUser:
        return user

    @router.post("/logout")
    def logout(token: str | None = Depends(bearer_token)) -> dict:
        if token:
            with connect() as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
                conn.commit()
        return {"ok": True}

    return router, current_user, optional_user
