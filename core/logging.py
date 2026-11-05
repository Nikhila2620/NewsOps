"""
NewsOps Revision 2 - Structured JSON Logging.

Provides JSON formatted logs with standard contextual fields:
task_id, source, stage, cost_estimate, and automatic secret redaction.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional


SENSITIVE_KEYS = {
    "password", "secret", "token", "key", "authorization", "session_secret",
    "agent_api_token", "github_oauth_client_secret", "reddit_client_secret",
}


def redact_sensitive_data(data: Any) -> Any:
    """Recursively redacts values for keys resembling secrets or tokens."""
    if isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_sensitive_data(v)
        return redacted
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects with NewsOps standard fields.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # NewsOps context fields if provided in extra
        for field in ("task_id", "source", "stage", "cost_estimate", "story_id", "room_key"):
            val = getattr(record, field, None)
            if val is not None:
                log_payload[field] = val

        # Handle exception information safely without exposing raw env / internal traces
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        redacted_payload = redact_sensitive_data(log_payload)
        return json.dumps(redacted_payload, default=str)


def setup_logger(name: str = "newsops", level: str = "INFO") -> logging.Logger:
    """Configures and returns the central structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logger()
