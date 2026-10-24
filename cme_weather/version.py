"""Software identity supplied by the release build or resolved from a Git checkout."""

import os
import subprocess
from pathlib import Path


def software_version() -> str:
    if supplied := os.environ.get("APP_VERSION"):
        return supplied
    script = Path(__file__).resolve().parents[1] / "tools" / "version.sh"
    if not script.is_file():
        return "0.0.0+unknown"
    try:
        return subprocess.check_output(["sh", str(script)], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "0.0.0+unknown"
