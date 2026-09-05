from app.dependency_graph import render_dependency_graph

# Design choices, for the record (see also the Phase 4 explanation):
#
# - System vs. user split: the persona, the output contract, and the
#   "don't hallucinate" instruction live in the system prompt and never
#   change; only the per-incident evidence goes in the user prompt. That
#   keeps every call structurally identical regardless of which anomaly
#   triggered it - the same reason you write a function once instead of
#   repeating its body inline at every call site.
# - Explicit epistemic humility ("if the evidence does not clearly point to
#   a cause, say so ... lower your confidence") is a deliberate
#   hallucination countermeasure: small local models will confidently
#   invent a plausible-sounding cause if you don't give them an explicit
#   permission (and instruction) to say "unclear" instead.
# - "Do not invent services ... not shown" constrains the model to the
#   4-service closed world it's actually being told about, instead of
#   drifting into generic cloud-outage tropes (DNS, load balancers, etc.)
#   that sound plausible but aren't grounded in anything provided.
# - A fixed JSON schema, restated field-by-field, makes the output
#   mechanically parseable (see app/analyzer.py's validation) so it can
#   feed a dashboard/ticket automatically instead of being prose a human
#   has to re-read and manually transcribe.
SYSTEM_PROMPT = """You are an experienced Site Reliability Engineer performing root cause \
analysis on a failure automatically flagged by an anomaly detector in a microservices system.

You will be given:
1. The static service call graph (which services call which).
2. The anomaly score and the threshold it exceeded (a higher score means the \
log sequence deviated more from the normal traffic patterns an LSTM \
autoencoder learned from clean traffic).
3. The full ordered sequence of structured log lines produced across all \
services for one traceId (one end-to-end business transaction), each with \
its relative timestamp, level, literal message, and the general Drain3 \
template it was mined into.

Explain WHY this sequence was flagged and WHERE the fault most likely \
originated, using only the evidence given to you. Do not invent services, \
causes, or log lines that are not shown. If the evidence does not clearly \
point to a cause, say so explicitly and lower your confidence instead of \
guessing.

Respond with a single JSON object and nothing else, matching exactly this \
schema:
{
  "rootCause": "one or two sentences naming the most likely originating service and failure",
  "affectedServices": ["service names involved, ordered by call chain"],
  "confidence": 0.0,
  "suggestedFix": "one concrete, actionable remediation step",
  "reasoning": "2-4 sentences walking through the specific log evidence that led to this conclusion"
}
confidence must be a number between 0.0 and 1.0."""


def build_user_prompt(anomaly: dict) -> str:
    events = anomaly.get("events", [])
    start_ts = events[0]["timestamp"] if events else None
    duration = (events[-1]["timestamp"] - start_ts) if len(events) > 1 else 0.0

    # Precomputing relative offsets (+0.42s) here, rather than handing the
    # model raw ISO-8601 timestamps and asking it to do the subtraction
    # itself, moves arithmetic the model is unreliable at into ordinary code
    # that isn't.
    log_lines = []
    for ev in events:
        offset = ev["timestamp"] - start_ts if start_ts is not None else 0.0
        log_lines.append(
            f'[+{offset:6.2f}s] {ev["service"]:20s} {ev["level"]:5s} {ev["message"]}\n'
            f'            template: "{ev["template"]}"'
        )

    return f"""## Service dependency graph
{render_dependency_graph()}

## Anomaly summary
traceId: {anomaly['traceId']}
anomaly score: {anomaly['score']} (flagged - exceeded the learned normal-traffic threshold of {anomaly['threshold']})
total trace duration: {duration:.2f}s

## Log sequence for this trace, in order
{chr(10).join(log_lines)}

Analyze this sequence and produce the JSON incident report described in your instructions."""
