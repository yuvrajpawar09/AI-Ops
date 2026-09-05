import json
import logging
import time

from app import config
from app.llm_client import OllamaClient
from app.prompt import SYSTEM_PROMPT, build_user_prompt
from app.remediation import maybe_remediate

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {"rootCause", "affectedServices", "confidence", "suggestedFix", "reasoning"}

_client = OllamaClient(config.OLLAMA_URL, config.OLLAMA_MODEL)


def analyze_anomaly(anomaly: dict) -> dict:
    user_prompt = build_user_prompt(anomaly)
    raw_output = _client.generate_report(SYSTEM_PROMPT, user_prompt)
    report = _parse_report(raw_output)

    if report.get("parseError"):
        # Nothing trustworthy to act on - a malformed report gets no
        # confidence score worth trusting, so remediation is skipped
        # unconditionally rather than falling through to the 0.0 default.
        outcome = "DIAGNOSED_ONLY"
        remediation_log = [{
            "timestamp": time.time(),
            "action": "evaluate",
            "result": "skipped",
            "reason": "model output could not be parsed - nothing trustworthy to act on",
        }]
    else:
        outcome, remediation_log = maybe_remediate(report, anomaly)

    return {
        "traceId": anomaly["traceId"],
        "anomalyScore": anomaly["score"],
        "threshold": anomaly["threshold"],
        "generatedAt": time.time(),
        "report": report,
        "outcome": outcome,
        "remediationLog": remediation_log,
        # Self-contained audit trail: the original failing sequence, so the
        # incident record explains itself without cross-referencing the
        # anomaly timeline by traceId.
        "beforeEvidence": anomaly.get("events", []),
    }


def _parse_report(raw_output: str) -> dict:
    """Never trust an LLM's output to be exactly what you asked for - even
    with format="json" forcing syntactic validity, the model can still
    return the wrong keys or an out-of-range confidence. Degrade to a
    clearly-marked fallback report instead of crashing the poller or
    silently storing garbage."""
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        logger.warning("LLM output was not valid JSON: %r", raw_output[:200])
        return _fallback_report("Model did not return valid JSON.", raw_output)

    if not isinstance(parsed, dict):
        return _fallback_report("Model returned JSON that wasn't an object.", raw_output)

    missing = REQUIRED_KEYS - parsed.keys()
    if missing:
        logger.warning("LLM output missing required keys: %s", missing)
        return _fallback_report(f"Model output missing fields: {sorted(missing)}", raw_output)

    try:
        parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))
    except (TypeError, ValueError):
        parsed["confidence"] = 0.0

    if not isinstance(parsed.get("affectedServices"), list):
        parsed["affectedServices"] = []

    parsed["parseError"] = False
    return parsed


def _fallback_report(reason: str, raw_output: str) -> dict:
    return {
        "rootCause": f"Could not determine root cause automatically: {reason}",
        "affectedServices": [],
        "confidence": 0.0,
        "suggestedFix": "Review the raw log context manually.",
        "reasoning": reason,
        "parseError": True,
        "rawModelOutput": raw_output[:2000],
    }
