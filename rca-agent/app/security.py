import secrets
import threading
import time
from collections import deque

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, Response, status

from app import config

CAPABILITIES = {
    "ADMIN": frozenset({"view", "acknowledge", "trigger", "manageUsers"}),
    "ENGINEER": frozenset({"view", "acknowledge"}),
    "VIEWER": frozenset({"view"}),
}


def issue_token(username: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iss": config.JWT_ISSUER,
        "iat": now,
        "exp": now + int(config.JWT_TTL_MINUTES * 60),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        config.JWT_SECRET,
        algorithms=[config.JWT_ALGORITHM],
        issuer=config.JWT_ISSUER,
        options={"require": ["exp", "iat", "sub", "iss"]},
    )


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        secure=config.SESSION_COOKIE_SECURE,
        path="/",
        max_age=int(config.JWT_TTL_MINUTES * 60),
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=config.SESSION_COOKIE_NAME,
        httponly=True,
        samesite="strict",
        secure=config.SESSION_COOKIE_SECURE,
        path="/",
    )


def service_headers() -> dict:
    return {"X-Service-Key": config.SERVICE_API_KEY}


def verify_service_key(provided: str | None) -> bool:
    if not provided:
        return False
    return secrets.compare_digest(provided, config.SERVICE_API_KEY)


_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required.",
)


def current_user(
    session: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME),
) -> dict:
    if not session:
        raise _UNAUTHENTICATED
    try:
        claims = decode_token(session)
    except jwt.PyJWTError:
        raise _UNAUTHENTICATED
    role = claims.get("role")
    if role not in CAPABILITIES:
        raise _UNAUTHENTICATED
    return {"username": claims["sub"], "role": role}


def optional_user(session: str | None) -> dict | None:
    if not session:
        return None
    try:
        claims = decode_token(session)
    except jwt.PyJWTError:
        return None
    role = claims.get("role")
    if role not in CAPABILITIES:
        return None
    return {"username": claims["sub"], "role": role}


def require(capability: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        if capability not in CAPABILITIES[user["role"]]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user['role']} is not permitted to {capability}.",
            )
        return user

    return dependency


class LoginRateLimiter:
    def __init__(self, attempts: int, window_seconds: float):
        self._attempts = attempts
        self._window = window_seconds
        self._lock = threading.Lock()
        self._failures: dict[str, deque] = {}

    @staticmethod
    def key(request: Request, username: str) -> str:
        client = request.client.host if request.client else "unknown"
        return f"{client}|{(username or '').lower()}"

    def check(self, key: str) -> float:
        now = time.time()
        with self._lock:
            bucket = self._failures.get(key)
            if not bucket:
                return 0.0
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._attempts:
                return self._window - (now - bucket[0])
        return 0.0

    def record_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            bucket = self._failures.setdefault(key, deque())
            bucket.append(now)
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(self._failures) > 2000:
                self._failures.clear()

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_limiter = LoginRateLimiter(
    config.LOGIN_RATE_LIMIT_ATTEMPTS,
    config.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
)
