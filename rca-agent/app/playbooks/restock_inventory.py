import logging
import re

import requests

from app import config
from app.playbooks.base import Playbook

logger = logging.getLogger(__name__)

_PRODUCT_RE = re.compile(r"\bPROD-\d+\b")

_STOCK_TERMS = ("insufficient stock", "out of stock", "out-of-stock", "stock", "inventory")


class RestockInventoryPlaybook(Playbook):
    name = "restock_inventory"
    description = (
        "A product ran out of stock, so paid orders fail at the inventory reservation step. "
        "Fix: add a safety buffer of stock for the affected product."
    )

    def matches(self, incident: dict) -> bool:
        root_cause, reasoning, affected = self._text_of(incident["report"])
        blob = f"{root_cause} {reasoning}"

        mentions_inventory = "inventory-service" in affected or "inventory" in blob
        mentions_stock = any(term in blob for term in _STOCK_TERMS)
        # Only actionable if we can actually tell WHICH product to restock -
        # a diagnosis we can't tie to a concrete product is not remediable
        # by this playbook, so decline rather than guess.
        return mentions_inventory and mentions_stock and self._affected_product(incident) is not None

    def apply(self, incident: dict) -> dict:
        product_id = self._affected_product(incident)
        payload = {"productId": product_id, "quantity": config.RESTOCK_BUFFER}
        resp = requests.post(
            f"{config.INVENTORY_SERVICE_URL}/admin/restock",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        return {
            "reason": f"Added {config.RESTOCK_BUFFER} units of {product_id} to inventory",
            "request": payload,
            "response": body,
        }

    def verify(self, incident: dict) -> bool:
        product_id = self._affected_product(incident)
        payload = {
            "customerId": "rca-agent-verification",
            "productId": product_id,
            "quantity": 1,
            "amount": 149.0,
        }
        resp = requests.post(
            f"{config.ORDER_SERVICE_URL}/orders",
            json=payload,
            timeout=15,
        )
        body = resp.json()
        confirmed = body.get("status") == "COMPLETED"

        if confirmed:
            reason = (
                f"Re-test order for {product_id} now returns COMPLETED "
                "- stock is available again, fix verified working"
            )
        else:
            reason = (
                f"verification order for {product_id} still shows "
                f"status={body.get('status')!r} - restock did not resolve it"
            )
        self.record_verification(incident, reason, request=payload, response=body)
        return confirmed

    def rollback(self, incident: dict) -> dict:
        """Deliberately a no-op, unlike reject_invalid_amount's real revert.

        Adding stock is not safely reversible the way flipping a boolean flag
        is. By the time verification runs, concurrent real orders may already
        have reserved some of the units we added, so "remove 50 units" is not
        the inverse of "add 50 units" - it could drive stock negative or
        cancel inventory that legitimate orders are now relying on. An
        unsafe undo is worse than no undo, so this playbook leaves the added
        stock in place (harmless: extra inventory breaks nothing) and
        escalates to a human instead. The asymmetry is intentional: rollback
        means "return to a safe state", which is not always "reverse the
        action".
        """
        product_id = self._affected_product(incident)
        logger.warning(
            "restock_inventory: no safe automatic undo for a stock increase (%s); "
            "leaving the added units in place and escalating to a human",
            product_id,
        )
        return {
            "result": "noop",
            "reason": (
                f"No safe automatic undo for a stock increase on {product_id}. "
                "Added units were left in place (extra stock is harmless) and the "
                "incident is escalated for human review."
            ),
        }

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _affected_product(incident: dict) -> str | None:
        """Finds the product id this incident is about.

        Prefers the log line that actually reports the shortage, since a
        trace mentions its product in several lines and the shortage line is
        the authoritative one. Falls back to any PROD-* in the events, then
        to the LLM's own text.
        """
        events = incident.get("events") or []

        for ev in events:
            message = (ev.get("message") or "")
            if "insufficient stock" in message.lower():
                match = _PRODUCT_RE.search(message)
                if match:
                    return match.group(0)

        for ev in events:
            match = _PRODUCT_RE.search(ev.get("message") or "")
            if match:
                return match.group(0)

        report = incident.get("report") or {}
        match = _PRODUCT_RE.search(
            f"{report.get('rootCause') or ''} {report.get('reasoning') or ''}"
        )
        return match.group(0) if match else None
