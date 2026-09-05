import time
from abc import ABC, abstractmethod


def log_entry(action: str, result: str, reason: str, **extra) -> dict:
    """One auditable line in an incident's remediationLog."""
    entry = {"timestamp": time.time(), "action": action, "result": result, "reason": reason}
    entry.update(extra)
    return entry


class Playbook(ABC):
    """One known failure pattern plus the safe procedure for fixing it.

    The orchestrator (app/remediation.py) owns the safety rules that apply to
    every playbook - the confidence gate, the wait before verifying, and the
    guarantee that a failed verification triggers rollback. A playbook only
    supplies the four pattern-specific steps below, so adding a new
    remediable failure never means re-implementing (or accidentally
    weakening) those rules.

    The `incident` dict passed to every method has the shape:
        {
          "traceId": str,
          "report":  <the LLM's structured incident report>,
          "events":  <the ordered log lines for that trace>,
        }

    Method contract:
      matches(incident)  -> bool
          Cheap, side-effect-free. Does this playbook's failure pattern
          describe this diagnosis? Must be conservative: a false positive
          here means acting on a system the playbook does not understand.

      apply(incident)    -> dict with keys {reason, request, response}
          Take the corrective action. Raise on failure - the orchestrator
          catches it, records it, and escalates without attempting rollback
          (nothing was applied, so there is nothing to undo).

      verify(incident)   -> bool
          Independently re-test that the fix actually worked. Because this
          returns a bare bool, it must also call self.record_verification()
          so the evidence it saw still reaches the audit log.

      rollback(incident) -> dict with keys {result, reason, ...}
          Undo the action. `result` is "reverted" when state was genuinely
          restored, or "noop" when this playbook has no safe undo (see
          restock_inventory for a documented example of the latter).
    """

    #: stable identifier shown in remediationLog entries
    name: str = "unnamed"
    #: one-line human description of the pattern this playbook handles
    description: str = ""

    @abstractmethod
    def matches(self, incident: dict) -> bool:
        ...

    @abstractmethod
    def apply(self, incident: dict) -> dict:
        ...

    @abstractmethod
    def verify(self, incident: dict) -> bool:
        ...

    @abstractmethod
    def rollback(self, incident: dict) -> dict:
        ...

    # -- helpers shared by every playbook -----------------------------------

    def record_verification(self, incident: dict, reason: str, **extra) -> None:
        """Stash what verify() actually observed. verify() returns only a
        bool, so without this the request/response bodies that justify an
        AUTO_RESOLVED verdict would never reach the audit trail."""
        incident["_verification"] = {"reason": reason, **extra}

    @staticmethod
    def _text_of(report: dict) -> tuple[str, str, list]:
        """Lowercased (rootCause, reasoning, affectedServices) for matching."""
        return (
            (report.get("rootCause") or "").lower(),
            (report.get("reasoning") or "").lower(),
            [s.lower() for s in report.get("affectedServices", [])],
        )
