# Static, hand-authored to match the Phase 1 call chain exactly. The agent
# doesn't try to infer topology from logs - it's handed the topology up
# front, the same way a human SRE already knows the architecture before
# they open a single dashboard. This is context the LLM has no way to
# reliably derive from a handful of log lines alone.
DEPENDENCY_GRAPH = {
    "order-service": ["payment-service", "inventory-service"],
    "payment-service": ["notification-service"],
    "inventory-service": [],
    "notification-service": [],
}


def render_dependency_graph() -> str:
    lines = []
    for service, calls in DEPENDENCY_GRAPH.items():
        target = ", ".join(calls) if calls else "(none)"
        lines.append(f"{service} calls: {target}")
    return "\n".join(lines)
