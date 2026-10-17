"""
Detect whether another copy of the API is already running (standalone service,
developer copy, ...). Two instances share a port and a FileMaker connection, so
we look for a listener on the API port. Standard library only: the debugger
must always work.
"""

import socket

DEFAULT_PORT = 8432
CONNECT_TIMEOUT_SECONDS = 1


def is_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    """True if something accepts TCP connections on host:port."""
    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


def check_single_instance(port: int = DEFAULT_PORT) -> dict:
    """Return {"ok": True} if no other instance is running, else ok=False with an error."""
    if is_port_listening(port):
        return {"ok": False, "error": f"Another instance is already running: something is listening on port {port}"}
    return {"ok": True}
