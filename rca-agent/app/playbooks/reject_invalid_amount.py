import logging

import requests

from app import config
from app.playbooks.base import Playbook

logger = logging.getLogger(__name__)

# order-service lets amount <= 0 sail all the way to payment-service before
# it is declined. The fix (order-service's rejectZeroAmount flag) is specific
# to that pattern, so matches() must confirm the diagnosis actually describes
# it - a generic "payment failed" report is not enough grounds to flip a
# system-wide config flag.
VERIFICATION_PAYLOAD = {
    "customerId": "rca-agent-verification",
    "productId": "PROD-1",
    "quantity": 1,
    "amount": 0,
}


class RejectInvalidAmountPlaybook(Playbook):
    name = "reject_invalid_amount"
    description = (
        "Invalid (non-positive) order amount is only rejected deep in payment-service. "
        "Fix: enable gateway-level validation in order-service so it is rejected immediately."
    )

    def matches(self, incident: dict) -> bool:
        root_cause, reasoning, affected = self._text_of(incident["report"])
        mentions_payment = (
            "payment-service" in affected or "payment" in root_cause or "payment" in reasoning
        )
        mentions_amount = "amount" in root_cause or "amount" in reasoning
        return mentions_payment and mentions_amount

    def apply(self, incident: dict) -> dict:
        resp = requests.post(
            f"{config.ORDER_SERVICE_URL}/admin/config",
            json={"rejectZeroAmount": True},
            timeout=10,
        )
        resp.raise_for_status()
        return {
            "reason": "Set rejectZeroAmount=true on order-service",
            "request": {"rejectZeroAmount": True},
            "response": resp.json(),
        }

    def verify(self, incident: dict) -> bool:
        resp = requests.post(
            f"{config.ORDER_SERVICE_URL}/orders",
            json=VERIFICATION_PAYLOAD,
            timeout=15,
        )
        body = resp.json()
        confirmed = body.get("status") == "REJECTED_AT_GATEWAY"

        if confirmed:
            reason = "Re-test with amount=0 now returns REJECTED_AT_GATEWAY - fix verified working"
        else:
            reason = (
                f"verification order still shows status={body.get('status')!r} "
                "- fix did not take effect"
            )
        self.record_verification(
            incident, reason, request=VERIFICATION_PAYLOAD, response=body
        )
        return confirmed

    def rollback(self, incident: dict) -> dict:
        resp = requests.post(
            f"{config.ORDER_SERVICE_URL}/admin/config",
            json={"rejectZeroAmount": False},
            timeout=10,
        )
        return {
            "result": "reverted",
            "reason": "Reverted rejectZeroAmount to false",
            "request": {"rejectZeroAmount": False},
            "response": resp.json(),
        }
