"""Vs Data."""
import logging
import os

from rich.logging import RichHandler

LEVEL = getattr(logging, os.environ.get("VS_DATA_LOGGING_LEVEL", "WARNING"), "WARNING")

logging.basicConfig(
    level=LEVEL,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("rich")

# Base directory for generated files (exports, caches, audit logs). Must be writable.
TMP_DIR = os.environ.get("VSDATA_TMP_DIR", "tmp")
