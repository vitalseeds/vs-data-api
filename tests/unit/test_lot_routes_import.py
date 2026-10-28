import subprocess
import sys

import pytest


@pytest.mark.parametrize("module", ["vs_data_api.lot_routes", "vs_data_api.main"])
def test_importable_first_in_a_fresh_interpreter(module):
    """No circular import: either module can be the first one loaded (make run, serve.py)."""
    result = subprocess.run([sys.executable, "-c", f"import {module}"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
