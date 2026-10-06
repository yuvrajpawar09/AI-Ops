import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.kafka_consumer import start_background_threads
from app.state import AppState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Built once at process import time: loads/resumes the Drain3 tree and
# (if present) the trained model, so neither happens per-request.
state = AppState(max_anomalies=config.MAX_ANOMALIES_STORED)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_background_threads(state)
    yield
    # Background threads are daemons - they die with the process, nothing to close.


app = FastAPI(title="AI-Ops Anomaly Detector", lifespan=lifespan)

# The Phase 5 dashboard (http://localhost:3000) polls this service's
# published port (http://localhost:8000) directly from the browser - a
# cross-origin request by the same-origin policy. No auth/cookies flow
# through this API, so a wide-open origin list is fine for a local demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "modelLoaded": state.scorer is not None,
        "featureVersion": config.FEATURE_VERSION,
        "reopenedTraces": state.buffer.reopened,
    }


@app.get("/anomalies")
def get_anomalies(limit: int = Query(50, ge=1, le=500)):
    items = state.anomaly_store.recent(limit)
    return {"count": len(items), "anomalies": items}
