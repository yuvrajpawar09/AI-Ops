import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.poller import start_background_poller
from app.store import AppState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

state = AppState(max_incidents=config.MAX_INCIDENTS_STORED)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_background_poller(state)
    yield


app = FastAPI(title="AI-Ops RCA Agent", lifespan=lifespan)

# Same reasoning as anomaly-detector: the dashboard's browser-side fetch()
# calls are cross-origin against this service's published port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/incidents")
def get_incidents(limit: int = Query(50, ge=1, le=500)):
    items = state.incident_store.recent(limit)
    return {"count": len(items), "incidents": items}
