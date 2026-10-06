import os
import secrets as pysecrets

import jwt
from fastapi import Cookie, Header, HTTPException, status


class MissingSecretError(RuntimeError):
    pass


PLACEHOLDER_EXACT = {"", "secret", "admin", "password", "todo", "xxx"}

PLACEHOLDER_FRAGMENTS = (
    "change-me",
    "change_me",
    "changeme",
    "replace-me",
    "replace_me",
    "replaceme",
    "placeholder",
    "your-secret",
    "your-password",
    "example",
    "xxxx",
)


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in PLACEHOLDER_EXACT:
        return True
    return any(fragment in lowered for fragment in PLACEHOLDER_FRAGMENTS)


def require_secret(name: str, min_length: int = 1) -> str:
    raw = os.environ.get(name)
    if raw is None:
        raise MissingSecretError(
            f"{name} is not set. Copy .env.example to .env and give it a real value."
        )
    value = raw.strip()
    if is_placeholder(value):
        raise MissingSecretError(
            f"{name} is still a placeholder value ({raw!r}). Replace it with a real secret."
        )
    if len(value) < min_length:
        raise MissingSecretError(
            f"{name} is only {len(value)} characters; at least {min_length} are required."
        )
    return value


JWT_SECRET = require_secret("JWT_SECRET", min_length=32)
SERVICE_API_KEY = require_secret("SERVICE_API_KEY", min_length=16)

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "aiops-rca-agent"
SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "aiops_session")

VIEW_ROLES = frozenset({"ADMIN", "ENGINEER", "VIEWER"})

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required.",
)


def require_reader(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    x_service_key: str | None = Header(default=None),
) -> dict:
    if x_service_key and pysecrets.compare_digest(x_service_key, SERVICE_API_KEY):
        return {"username": "service", "role": "SERVICE"}

    if not session:
        raise _UNAUTHENTICATED

    try:
        claims = jwt.decode(
            session,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
    except jwt.PyJWTError:
        raise _UNAUTHENTICATED

    role = claims.get("role")
    if role not in VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {role} is not permitted to read anomalies.",
        )
    return {"username": claims["sub"], "role": role}
