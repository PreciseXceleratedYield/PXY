"""Persisted post-square-off cooldown state read by the signal router."""
import json
import math
import os
import tempfile
import time
from pathlib import Path

from syscnfgpxy import EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
COOLDOWN_FILE = WEB_DIR / ".pxy_post_squareoff_cooldown.json"


def cooldown_remaining(now=None):
    """Return seconds remaining in the persisted whole-engine cooldown."""
    try:
        with COOLDOWN_FILE.open("r", encoding="utf-8") as state_file:
            state = json.load(state_file)
    except FileNotFoundError:
        return 0.0

    until = float(state["cooldown_until"])
    if not math.isfinite(until):
        raise ValueError(f"Invalid square-off cooldown timestamp in {COOLDOWN_FILE}")
    return max(0.0, until - (time.time() if now is None else now))


def start_cooldown(now=None):
    """Persist a full cooldown window, including across engine restarts."""
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    until = (time.time() if now is None else now) + EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=WEB_DIR, delete=False
        ) as state_file:
            temp_path = Path(state_file.name)
            json.dump({"cooldown_until": until}, state_file)
            state_file.flush()
            os.fsync(state_file.fileno())
        os.replace(temp_path, COOLDOWN_FILE)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
