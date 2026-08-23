import logging
import sys
from typing import Any

import structlog


def configure(level: int = logging.INFO) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def log(event: str, **fields: Any) -> None:
    """Emit one structured event.

    Callers pass identifiers, never content: a resume_id, a page number, a detector id. The
    document text is the one thing that must never reach a log line, because the whole
    premise of this system is that it is hostile input and logs get shipped somewhere else.
    """
    structlog.get_logger("careerlayer").info(event, **fields)
