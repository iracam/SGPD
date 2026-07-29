"""Structured logging helpers."""

import json
import logging
from datetime import UTC, datetime

from config.middleware import correlation_id


class JsonFormatter(logging.Formatter):
    """Serialize safe log metadata as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        # Only explicitly allowlisted, non-sensitive metadata is projected.
        # This keeps operational account logs useful without risking usernames,
        # e-mails, request bodies or credentials in stdout.
        for attribute in (
            "query_name",
            "elapsed_ms",
            "row_count",
            "event_type",
            "actor_id",
            "target_user_id",
            "role_id",
            "assignment_id",
            "scope_type",
            "scope_key",
            "initial_role_requested",
            "outcome",
        ):
            if hasattr(record, attribute):
                payload[attribute] = getattr(record, attribute)
        return json.dumps(payload, ensure_ascii=False)
