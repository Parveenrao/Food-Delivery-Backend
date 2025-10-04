import logging
import structlog
import sys
from app.config import settings

import logging
import sys
import structlog
from app.config import settings

def configure_logging():
    """
    Configure Python logging and structlog for structured logging.
    """
    # 1️⃣ Configure base Python logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # 2️⃣ Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,   # Merge context vars like request_id
            structlog.processors.add_log_level,        # Add log level
            structlog.processors.StackInfoRenderer(),  # Include stack info if available
            structlog.dev.set_exc_info,                # Include exception info
            structlog.processors.TimeStamper(fmt="iso"),  # Add timestamp
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=False,
    )

# 3️⃣ Get global logger
logger = structlog.get_logger()
