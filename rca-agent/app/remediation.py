import logging
import time

import requests

from app import config

logger = logging.getLogger(__name__)

# The one known-fixable pattern this phase handles: order-service lets
# amount <= 0 sail all the way to payment-service before it's declined.
# The fix (order-service's rejectZeroAmount flag) is specific to that
# pattern, so remediation must confirm the diagnosis actually matches it -
# a generic "payment failed" report is not enough grounds to flip a
# system-wide config flag.
VERIFICATION_PAYLOAD = {
    "customerId": "rca-agent-verification",
    "productId": "PROD-1",
    "quantity": 1,
    "amount": 0,
}


def _entry(action: str, result: str, reason: str, **extra) -> dict:
    entry = {"timestamp": time.time(), "action": action, "result": result, "reason": reason}
    entry.update(extra)
    return entry


def matches_zero_amount_pattern(report: dict) -> bool:
    root_cause = (report.get("rootCause") or "").lower()
    reasoning = (report.get("reasoning") or "").lower()
    affected = [s.lower() for s in report.get("affectedServices", [])]

    mentions_payment = "payment-service" in affected or "payment" in root_cause or "payment" in reasoning
    mentions_amount = "amount" in root_cause or "amount" in reasoning
    return mentions_payment and mentions_amount


def maybe_remediate(report: dict, anomaly: dict) -> tuple[str, list]:
    """Decides whether to act on an incident and, if so, applies the known
    fix, re-tests it for real, and rolls back if the re-test doesn't confirm
    it worked. Returns (outcome, remediation_log); outcome is one of
    DIAGNOSED_ONLY / AUTO_RESOLVED / ESCALATED_TO_HUMAN.

    Safety rules enforced here, not just documented:
      - never act below REMEDIATION_CONFIDENCE_THRESHOLD
      - never declare success without re-testing actual behavior
      - always have a rollback path if verification fails
      - every decision - act or not - is appended to remediation_log
    """
    trace_id = anomaly.get("traceId")
    remediation_log = []
    confidence = report.get("confidence", 0.0)
    pattern_matched = matches_zero_amount_pattern(report)

    if confidence < config.REMEDIATION_CONFIDENCE_THRESHOLD or not pattern_matched:
        if confidence < config.REMEDIATION_CONFIDENCE_THRESHOLD:
            reason = f"confidence {confidence:.2f} below threshold {config.REMEDIATION_CONFIDENCE_THRESHOLD}"
        else:
            reason = "diagnosis does not match the known invalid-amount/payment-decline pattern"
        remediation_log.append(_entry("evaluate", "skipped", reason))
        logger.info("Not remediating trace %s: %s", trace_id, reason)
        return "DIAGNOSED_ONLY", remediation_log

    remediation_log.append(_entry(
        "evaluate", "attempting",
        f"confidence {confidence:.2f} >= {config.REMEDIATION_CONFIDENCE_THRESHOLD} and pattern matched",
    ))

    # 1. Apply the fix at the gateway.
    try:
        apply_resp = requests.post(
            f"{config.ORDER_SERVICE_URL}/admin/config",
            json={"rejectZeroAmount": True},
            timeout=10,
        )
        apply_resp.raise_for_status()
        apply_body = apply_resp.json()
    except (requests.RequestException, ValueError) as ex:
        remediation_log.append(_entry("apply_config", "error", str(ex)))
        logger.error("Remediation failed to apply config for trace %s: %s", trace_id, ex)
        return "ESCALATED_TO_HUMAN", remediation_log

    remediation_log.append(_entry(
        "apply_config", "applied", "Set rejectZeroAmount=true on order-service",
        request={"rejectZeroAmount": True}, response=apply_body,
    ))

    # 2. Never declare success without re-testing actual behavior.
    time.sleep(config.REMEDIATION_VERIFY_DELAY_SECONDS)

    try:
        verify_resp = requests.post(
            f"{config.ORDER_SERVICE_URL}/orders",
            json=VERIFICATION_PAYLOAD,
            timeout=15,
        )
        verify_body = verify_resp.json()
    except (requests.RequestException, ValueError) as ex:
        remediation_log.append(_entry("verify", "error", str(ex)))
        return _rollback(remediation_log, trace_id, f"verification request failed: {ex}")

    if verify_body.get("status") == "REJECTED_AT_GATEWAY":
        remediation_log.append(_entry(
            "verify", "confirmed",
            "Re-test with amount=0 now returns REJECTED_AT_GATEWAY - fix verified working",
            request=VERIFICATION_PAYLOAD, response=verify_body,
        ))
        logger.info("Remediation verified for trace %s - fix confirmed working", trace_id)
        return "AUTO_RESOLVED", remediation_log

    remediation_log.append(_entry(
        "verify", "failed",
        f"verification order still shows status={verify_body.get('status')!r} - fix did not take effect",
        request=VERIFICATION_PAYLOAD, response=verify_body,
    ))
    return _rollback(remediation_log, trace_id, "verification did not confirm the fix")


def _rollback(remediation_log: list, trace_id: str, reason: str) -> tuple[str, list]:
    logger.warning("Rolling back remediation for trace %s: %s", trace_id, reason)
    try:
        rollback_resp = requests.post(
            f"{config.ORDER_SERVICE_URL}/admin/config",
            json={"rejectZeroAmount": False},
            timeout=10,
        )
        rollback_body = rollback_resp.json()
        remediation_log.append(_entry(
            "rollback", "reverted", "Reverted rejectZeroAmount to false",
            request={"rejectZeroAmount": False}, response=rollback_body,
        ))
    except (requests.RequestException, ValueError) as ex:
        remediation_log.append(_entry("rollback", "error", str(ex)))
        logger.error("Rollback itself failed for trace %s: %s", trace_id, ex)

    return "ESCALATED_TO_HUMAN", remediation_log
