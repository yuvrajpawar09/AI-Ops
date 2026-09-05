import logging
import time

from app import config
from app.playbooks.base import log_entry
from app.playbooks.reject_invalid_amount import RejectInvalidAmountPlaybook
from app.playbooks.restock_inventory import RestockInventoryPlaybook

logger = logging.getLogger(__name__)

# Registered playbooks, tried in order; the first whose matches() returns
# True handles the incident. Order matters only if two playbooks could match
# the same diagnosis - keep the more specific pattern first.
PLAYBOOKS = [
    RejectInvalidAmountPlaybook(),
    RestockInventoryPlaybook(),
]


def maybe_remediate(report: dict, anomaly: dict) -> tuple[str, list]:
    """Decides whether to act on an incident and, if so, runs the matching
    playbook: apply -> wait -> verify -> rollback if verification failed.
    Returns (outcome, remediation_log); outcome is one of
    DIAGNOSED_ONLY / AUTO_RESOLVED / ESCALATED_TO_HUMAN.

    The safety rules live here rather than in the playbooks, so every
    playbook inherits them and none can weaken them:
      - never act below REMEDIATION_CONFIDENCE_THRESHOLD
      - never act without a playbook that recognizes the failure pattern
      - never declare success without re-testing actual behavior
      - always attempt rollback when verification does not confirm the fix
      - every decision - act or not - is appended to remediation_log
    """
    trace_id = anomaly.get("traceId")
    remediation_log = []
    confidence = report.get("confidence", 0.0)

    incident = {
        "traceId": trace_id,
        "report": report,
        "events": anomaly.get("events", []),
    }

    if confidence < config.REMEDIATION_CONFIDENCE_THRESHOLD:
        reason = f"confidence {confidence:.2f} below threshold {config.REMEDIATION_CONFIDENCE_THRESHOLD}"
        remediation_log.append(log_entry("evaluate", "skipped", reason))
        logger.info("Not remediating trace %s: %s", trace_id, reason)
        return "DIAGNOSED_ONLY", remediation_log

    playbook = _select_playbook(incident)
    if playbook is None:
        reason = "diagnosis does not match any registered playbook"
        remediation_log.append(log_entry("evaluate", "skipped", reason))
        logger.info("Not remediating trace %s: %s", trace_id, reason)
        return "DIAGNOSED_ONLY", remediation_log

    remediation_log.append(log_entry(
        "evaluate", "attempting",
        f"confidence {confidence:.2f} >= {config.REMEDIATION_CONFIDENCE_THRESHOLD} "
        f"and pattern matched playbook '{playbook.name}'",
        playbook=playbook.name,
    ))

    # 1. Apply the corrective action.
    try:
        applied = playbook.apply(incident)
    except Exception as ex:
        remediation_log.append(log_entry("apply", "error", str(ex), playbook=playbook.name))
        logger.error(
            "Playbook '%s' failed to apply for trace %s: %s", playbook.name, trace_id, ex
        )
        # Nothing was applied, so there is nothing to roll back.
        return "ESCALATED_TO_HUMAN", remediation_log

    remediation_log.append(log_entry(
        "apply", "applied", applied.get("reason", ""),
        playbook=playbook.name,
        request=applied.get("request"),
        response=applied.get("response"),
    ))

    # 2. Never declare success without re-testing actual behavior.
    time.sleep(config.REMEDIATION_VERIFY_DELAY_SECONDS)

    try:
        confirmed = playbook.verify(incident)
        verification = incident.get("_verification", {})
    except Exception as ex:
        remediation_log.append(log_entry("verify", "error", str(ex), playbook=playbook.name))
        return _rollback(playbook, incident, remediation_log, trace_id,
                         f"verification request failed: {ex}")

    if confirmed:
        remediation_log.append(log_entry(
            "verify", "confirmed", verification.get("reason", "fix verified working"),
            playbook=playbook.name,
            request=verification.get("request"),
            response=verification.get("response"),
        ))
        logger.info(
            "Playbook '%s' verified for trace %s - fix confirmed working",
            playbook.name, trace_id,
        )
        return "AUTO_RESOLVED", remediation_log

    remediation_log.append(log_entry(
        "verify", "failed", verification.get("reason", "fix did not take effect"),
        playbook=playbook.name,
        request=verification.get("request"),
        response=verification.get("response"),
    ))
    return _rollback(playbook, incident, remediation_log, trace_id,
                     "verification did not confirm the fix")


def _select_playbook(incident: dict):
    for playbook in PLAYBOOKS:
        try:
            if playbook.matches(incident):
                return playbook
        except Exception:
            # A broken matcher must not take down remediation for every other
            # playbook - skip it and keep looking.
            logger.exception("Playbook '%s' matches() raised; skipping it", playbook.name)
    return None


def _rollback(playbook, incident: dict, remediation_log: list, trace_id: str,
              reason: str) -> tuple[str, list]:
    logger.warning(
        "Rolling back playbook '%s' for trace %s: %s", playbook.name, trace_id, reason
    )
    try:
        result = playbook.rollback(incident)
        remediation_log.append(log_entry(
            "rollback", result.get("result", "reverted"), result.get("reason", ""),
            playbook=playbook.name,
            request=result.get("request"),
            response=result.get("response"),
        ))
    except Exception as ex:
        remediation_log.append(log_entry("rollback", "error", str(ex), playbook=playbook.name))
        logger.error(
            "Rollback itself failed for playbook '%s' on trace %s: %s",
            playbook.name, trace_id, ex,
        )

    return "ESCALATED_TO_HUMAN", remediation_log
