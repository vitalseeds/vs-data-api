"""
Load environment variables from a ``.env`` file.

Called once from ``vs_data_api/__init__.py`` so that it runs before anything
reads ``os.environ`` (``Settings`` as well as the modules that read variables
directly, eg ``VSDATA_TMP_DIR``).

Real environment variables always win over the file, so direnv, ``dotenv run``,
service managers and CI keep working unchanged. python-dotenv handles quoting
and an optional ``export`` prefix, so a value written as ``KEY="value"`` loads
as ``value`` (unlike ``nssm``, which keeps the quotes).

Search order (first existing wins, all are loaded with ``override=False``):

1. the file named by ``VSDATA_ENV_FILE``, if set (nothing else is loaded)
2. ``.env`` in the repo root (the folder holding ``src/``)
3. ``.env`` in the current working directory
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE_VAR = "VSDATA_ENV_FILE"
REPO_ROOT = Path(__file__).resolve().parents[2]


def env_file_candidates() -> list:
    explicit = os.environ.get(ENV_FILE_VAR)
    if explicit:
        return [Path(explicit)]
    return [REPO_ROOT / ".env", Path.cwd() / ".env"]


def load_env_file():
    """Load the first existing candidate file. Returns its path, or None."""
    for path in env_file_candidates():
        if path.is_file():
            load_dotenv(path, override=False)
            return path
    return None
