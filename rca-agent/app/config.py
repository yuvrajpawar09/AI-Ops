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
