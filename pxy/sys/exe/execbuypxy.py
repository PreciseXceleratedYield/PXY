#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# ----------------- CONFIGURATION & CONSTANTS -----------------
CBUY_LOCK_FILE_NAME = ".cbuy_lock.json"
CBUY_COUNT_FILE_NAME = ".cbuy_count.json"

_LOCK_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    CBUY_LOCK_FILE_NAME,
)
# FIX: Fast RAM tracker to intercept high-speed duplicate loops instantly
_RAM_LOCKS = {}

_COUNT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    CBUY_COUNT_FILE_NAME,
)

def _load_locks():
    if not os.path.exists(_LOCK_FILE):
        return {}
    try:
        with open(_LOCK_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_locks(data):
    try:
        with open(_LOCK_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def _recent(data, key, secs):
    """Checks both instant RAM locks and disk data to prevent loop racing."""
    now = datetime.now().timestamp()
    
    # Check lightning-fast RAM first
    if key in _RAM_LOCKS:
        if (now - _RAM_LOCKS[key]) < secs:
            return True
            
    # Fallback check on standard disk data
    if not data or key not in data:
        return False
    try:
        ts = float(data[key])
        return (now - ts) < secs
    except (ValueError, TypeError):
        return False

def _mark_lock(key):
    """Locks the action instantly in RAM, then safely writes to disk file."""
    now = datetime.now().timestamp()
    
    # 1. Update RAM instantly (Takes nanoseconds, completely blocking Cycle 2)
    _RAM_LOCKS[key] = now
    
    # 2. Proceed with your standard disk storage sync
    data = _load_locks()
    data[key] = str(now)
    _save_locks(data)

def _load_counts():
    if not os.path.exists(_COUNT_FILE):
        return {"count": 0}
    try:
        with open(_COUNT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"count": 0}

def _save_counts(data):
    try:
        with open(_COUNT_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def _count_fire():
    counts = _load_counts()
    counts["count"] = counts.get("count", 0) + 1
    _save_counts(counts)

def check_counter_leg(remaining_df):
    """
    Evaluates open positions and dynamically triggers pxybuype or pxybuyce 
    with calculated offsets as a fully detached process context.
    """
    if remaining_df is None or remaining_df.empty:
        return

    for _, row in remaining_df.iterrows():
        symbol = str(row.get("symbol", "")).upper()
        if not symbol:
            continue

        # Determine target counter script based on the open position type
        if symbol.endswith("CE"):
            script_name = "pxybuype"
            lock_key = f"CBUY|{script_name}"
        elif symbol.endswith("PE"):
            script_name = "pxybuyce"
            lock_key = f"CBUY|{script_name}"
        else:
            continue

        # Check existing locks across memory and storage (limit to 10 second window)
        locks = _load_locks()
        if _recent(locks, lock_key, 10):
            continue

        # Calculate contract step offsets (placeholder for internal logic)
        offset = 0 
        
        # Resolve target paths cleanly
        here = Path(__file__).resolve().parent
        parent_dir = here.parent
        
        # Hunt inside pxy root or sys directories
        possible_paths = [
            here / script_name,
            parent_dir / script_name,
            parent_dir / "pxy" / script_name
        ]
        
        path = None
        for p in possible_paths:
            if p.exists():
                path = str(p)
                break
                
        if not path:
            print(f"{Fore.RED} ❌ Script execution failed -> {script_name} not found.")
            continue

        # Lock and count before launch to reduce duplicate counter-buy orders.
        _mark_lock(lock_key)
        _count_fire()

        # FIX: Added DEVNULL routing and start_new_session to prevent parent engine crashes
        try:
            subprocess.Popen(
                ["bash", path, str(offset)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            print(
                f"{Fore.MAGENTA}{Style.BRIGHT} ⚡ FIRED COUNTER-BUY: "
                f"{script_name} {offset}"
            )
        except Exception as e:
            print(f"{Fore.RED} ❌ Failed to spawn background process: {e}")