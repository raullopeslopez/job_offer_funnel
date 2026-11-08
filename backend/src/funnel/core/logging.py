import logging

import structlog


def configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Plain tracebacks: the default rich renderer dumps boxes and locals (megabytes).
            structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
    )
