import os

ANOMALY_DETECTOR_URL = os.environ.get("ANOMALY_DETECTOR_URL", "http://anomaly-detector:8000")
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "10"))

# Override to http://host.docker.internal:11434 to use a host-installed
# Ollama instead of the containerized one (e.g. for GPU acceleration).
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
# Generous on purpose: Ollama unloads a model from memory after ~5 minutes
# idle (its default keep_alive), and reloading a 3B model plus running a
# CPU-only inference pass under load can plausibly take over 120s - a demo
# with gaps between triggers will hit exactly this cold-start path.
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "240"))

MAX_INCIDENTS_STORED = int(os.environ.get("MAX_INCIDENTS_STORED", "200"))

# Phase 6: auto-remediation acts on service admin endpoints directly.
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8081")
INVENTORY_SERVICE_URL = os.environ.get("INVENTORY_SERVICE_URL", "http://inventory-service:8083")
# Safety buffer the restock_inventory playbook adds to an exhausted product.
RESTOCK_BUFFER = int(os.environ.get("RESTOCK_BUFFER", "50"))
REMEDIATION_CONFIDENCE_THRESHOLD = float(os.environ.get("REMEDIATION_CONFIDENCE_THRESHOLD", "0.85"))
REMEDIATION_VERIFY_DELAY_SECONDS = float(os.environ.get("REMEDIATION_VERIFY_DELAY_SECONDS", "2"))


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
ADMIN_USERNAME = require_secret("ADMIN_USERNAME", min_length=3)
ADMIN_PASSWORD = require_secret("ADMIN_PASSWORD", min_length=8)

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "aiops-rca-agent"
JWT_TTL_MINUTES = float(os.environ.get("JWT_TTL_MINUTES", "30"))

SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "aiops_session")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

USERS_DB_PATH = os.environ.get("USERS_DB_PATH", "/data/users.db")

LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = float(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60"))
