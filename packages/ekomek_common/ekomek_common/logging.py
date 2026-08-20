import json
import logging
import re
import sys
from datetime import datetime, timezone

from ekomek_common.correlation import current_correlation_id, current_request_id

IIN_PATTERN = re.compile(r"\b\d{12}\b")
IIN_IN_PATH = re.compile(r"(iin[=:/]\s*)\d{12}", re.IGNORECASE)
DOCUMENT_HINT = re.compile(
    r"(document(?:_number)?[=:/\s]+)\d{6,}",
    re.IGNORECASE,
)


def redact_sensitive(text):
    if not text:
        return text
    redacted = IIN_IN_PATH.sub(r"\1[REDACTED_IIN]", str(text))
    redacted = IIN_PATTERN.sub("[REDACTED_IIN]", redacted)
    return DOCUMENT_HINT.sub(r"\1[REDACTED]", redacted)


class RedactSensitiveFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = redact_sensitive(record.msg)
        if record.args:
            record.args = tuple(
                redact_sensitive(arg) if isinstance(arg, str) else arg for arg in record.args
            )
        return True


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive(record.getMessage()),
            "service": getattr(record, "service", None) or record.__dict__.get("service"),
            "request_id": current_request_id() or None,
            "correlation_id": current_correlation_id() or None,
        }
        if record.exc_info:
            payload["exception"] = redact_sensitive(self.formatException(record.exc_info))
        return json.dumps({key: value for key, value in payload.items() if value is not None})


def configure_logging(service_name):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    handler.addFilter(RedactSensitiveFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logging.LoggerAdapter(root, {"service": service_name})
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "redact_sensitive": {
                "()": "ekomek_common.logging.RedactSensitiveFilter",
            }
        },
        "formatters": {
            "json": {
                "()": "ekomek_common.logging.StructuredJsonFormatter",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["redact_sensitive"],
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
    }
