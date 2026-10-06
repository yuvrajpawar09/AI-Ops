import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app import config, security, trigger, users_db
from app.poller import start_background_poller
from app.store import AppState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

state = AppState(max_incidents=config.MAX_INCIDENTS_STORED)


@asynccontextmanager
async def lifespan(app: FastAPI):
    users_db.init_db()
    start_background_poller(state)
    yield


app = FastAPI(title="AI-Ops RCA Agent", lifespan=lifespan)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=256)
    role: str


class RoleRequest(BaseModel):
    role: str


class TriggerRequest(BaseModel):
    scenario: str


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login")
def login(request: Request, body: LoginRequest, response: Response):
    key = security.login_limiter.key(request, body.username)
    retry_after = security.login_limiter.check(key)
    if retry_after > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again shortly.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )

    record = users_db.get_user(body.username.strip())
    if record is None or not users_db.verify_password(body.password, record["password_hash"]):
        security.login_limiter.record_failure(key)
        logger.warning("Failed login attempt for %r", body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    security.login_limiter.reset(key)
    token = security.issue_token(record["username"], record["role"])
    security.set_session_cookie(response, token)
    logger.info("User %r signed in as %s", record["username"], record["role"])
    return {"user": {"username": record["username"], "role": record["role"]}}


@app.get("/auth/me")
def me(session: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME)):
    return {"user": security.optional_user(session)}


@app.post("/auth/logout")
def logout(response: Response):
    security.clear_session_cookie(response)
    return {"status": "signed-out"}


@app.get("/incidents")
def get_incidents(
    limit: int = Query(50, ge=1, le=500),
    user: dict = Depends(security.require("view")),
):
    items = state.incident_store.recent(limit)
    return {"count": len(items), "incidents": items}


@app.post("/incidents/{trace_id}/acknowledge")
def acknowledge_incident(
    trace_id: str,
    user: dict = Depends(security.require("acknowledge")),
):
    updated = state.incident_store.acknowledge(trace_id, user["username"])
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown traceId.")
    logger.info("Incident %s acknowledged by %r", trace_id, user["username"])
    return {"incident": updated}


@app.post("/trigger")
def post_trigger(
    body: TriggerRequest,
    user: dict = Depends(security.require("trigger")),
):
    if body.scenario not in trigger.SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario. Valid: {', '.join(sorted(trigger.SCENARIOS))}.",
        )
    try:
        return trigger.place_test_order(body.scenario, user["username"])
    except Exception as exc:
        logger.exception("Test order failed for scenario %s", body.scenario)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"order-service did not accept the test order: {exc}",
        )


@app.get("/users")
def get_users(user: dict = Depends(security.require("manageUsers"))):
    return {
        "users": [
            {"username": u["username"], "role": u["role"], "createdAt": _iso(u["created_at"])}
            for u in users_db.list_users()
        ]
    }


@app.post("/users", status_code=status.HTTP_201_CREATED)
def post_user(body: CreateUserRequest, user: dict = Depends(security.require("manageUsers"))):
    try:
        created = users_db.create_user(body.username, body.password, body.role)
    except users_db.UserError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.warning("User %r created %r as %s", user["username"], created["username"], created["role"])
    return {"user": {"username": created["username"], "role": created["role"]}}


@app.patch("/users/{username}/role")
def patch_user_role(
    username: str,
    body: RoleRequest,
    user: dict = Depends(security.require("manageUsers")),
):
    if username == user["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role.",
        )
    try:
        updated = users_db.set_role(username, body.role)
    except users_db.UserError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.warning("User %r set role of %r to %s", user["username"], username, body.role)
    return {"user": updated}
