"""Best-effort, nonblocking structured execution audit for PXY.

No Telegram, broker calls, or trading decisions. Append-only JSONL.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

AUDIT_FILE = Path(os.environ.get("PXY_AUDIT_FILE", str(Path.home() / ".pxy" / "audit" / "engine.jsonl")))

def record(component, status, **details):
    """Write one audit event; never raise into trading code."""
    try:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "time": datetime.now(timezone.utc).isoformat(),
            "component": str(component),
            "status": str(status),
            "pid": os.getpid(),
            **details,
        }
        # O_APPEND keeps concurrent writers from overwriting one another.
        fd = os.open(str(AUDIT_FILE), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, (json.dumps(event, default=str, ensure_ascii=False) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except Exception:
        pass
