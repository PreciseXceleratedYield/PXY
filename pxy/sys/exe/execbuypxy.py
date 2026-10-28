#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

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
            json.dump(data, f)
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

def _count_fire():
    try:
        count = 0
        if os.path.exists(_COUNT_FILE):
            with open(_COUNT_FILE, "r") as f:
                count = int(f.read().strip() or 0)
        count += 1
        with open(_COUNT_FILE, "w") as f:
            f.write(str(count))
    except Exception:
        pass

def check_counter_leg(remaining_df):
    """Evaluates held positions and triggers required counter leg hedges cleanly."""
    if remaining_df is None or remaining_df.empty:
        return

    # Check if we have open options positions to hedge
    for _, row in remaining_df.iterrows():
        symbol = str(row.get("symbol", "")).upper()
        if not symbol:
            continue
            
        # Determine the side that requires a counter-leg hedge
        side = None
        if symbol.endswith("PE"):
            side = "CE"  # We hold PE, so we need to buy CE
        elif symbol.endswith("CE"):
            side = "PE"  # We hold CE, so we need to buy PE
            
        if not side:
            continue

        lock_key = f"CBUY|{side}"
        locks = _load_locks()
        
        # Prevent duplicate orders within 15 seconds window
        if _recent(locks, lock_key, 15):
            continue

        script_name = "pxybuyce" if side == "CE" else "pxybuype"
        
        # FIX: Compute absolute path relative to this script directory to avoid file-not-found loop drops
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, script_name)
        
        # Quick check if path exists locally, otherwise look one level up in the repository layout
        if not os.path.exists(path):
            path = os.path.join(os.path.dirname(base_dir), script_name)

        offset = 0 # Default strike offset calculation logic placeholder
        
        # Lock and count before launch to reduce duplicate counter-buy orders.
        _mark_lock(lock_key)
        _count_fire()

        # FIX: Added DEVNULL routing, absolute execution, and start_new_session to prevent parent engine crashes
        try:
            subprocess.Popen(
                ["bash", path, str(offset)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            print(
                f"{Fore.MAGENTA}{Style.BRIGHT} ⚡ FIRED COUNTER-BUY: {script_name} {offset}"
            )
        except Exception as e:
            print(f"{Fore.RED} ❌ Failed to spawn background process {script_name}: {e}")
