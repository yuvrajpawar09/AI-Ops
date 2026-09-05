from datetime import datetime, timezone

from dateutil import parser as date_parser


def parse_timestamp(value) -> float:
    """Parses the ISO-8601 "timestamp" field Logback attaches to every log
    line into epoch seconds. Falls back to "now" if missing or unparsable,
    so one malformed field never crashes the consumer thread."""
    if not value:
        return datetime.now(timezone.utc).timestamp()
    try:
        return date_parser.isoparse(value).timestamp()
    except (ValueError, TypeError):
        return datetime.now(timezone.utc).timestamp()
