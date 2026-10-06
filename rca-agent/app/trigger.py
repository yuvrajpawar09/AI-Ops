import logging

import requests

from app import config

logger = logging.getLogger(__name__)

SCENARIOS = {
    "normal": {
        "customerId": "dashboard-trigger",
        "productId": "PROD-1",
        "quantity": 1,
        "amount": 199.0,
    },
    "out_of_stock": {
        "customerId": "dashboard-trigger",
        "productId": "PROD-3",
        "quantity": 5,
        "amount": 99.0,
    },
    "payment_failure": {
        "customerId": "dashboard-trigger",
        "productId": "PROD-1",
        "quantity": 1,
        "amount": 0,
    },
}


def place_test_order(scenario: str, username: str) -> dict:
    payload = dict(SCENARIOS[scenario])
    payload["customerId"] = f"dashboard-{username}"

    resp = requests.post(
        f"{config.ORDER_SERVICE_URL}/orders",
        json=payload,
        timeout=20,
    )
    body = {}
    try:
        body = resp.json()
    except ValueError:
        body = {}

    logger.warning(
        "Test order placed by %r (scenario=%s) -> HTTP %s status=%s trace=%s",
        username,
        scenario,
        resp.status_code,
        body.get("status"),
        body.get("traceId"),
    )

    return {
        "scenario": scenario,
        "httpStatus": resp.status_code,
        "status": body.get("status") or f"HTTP {resp.status_code}",
        "traceId": body.get("traceId"),
        "message": body.get("message"),
        "request": payload,
    }
