"""Vs Data."""
import os
import logging
from rich.logging import RichHandler

LEVEL = getattr(logging, os.environ.get("VS_DATA_LOGGING_LEVEL", "WARNING"), "WARNING")

logging.basicConfig(
    level=LEVEL,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("rich")
