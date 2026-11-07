
# syspxy.py
import json
import math
import os
import time
import tempfile
from pathlib import Path
from datetime import datetime

from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS,
)
from sysdashpxy import get_full_snapshot
from sysictrpxy import export_supertrend_json
from syscnfgpxy import SYSMKTPXY_ENTRY_FILTER
from syssmapxy import get_sma_signal
from syssdirpxy import get_structure_direction


def _notify_stale_market_data(core):
    """Print stale market-data diagnostics for the independent log monitor."""
    if not core.get("market_data_stale", False):
        return
    age = core.get("market_data_age_seconds")
    candle_time = core.get("market_data_timestamp", "unknown")
    print(
        "⚠️ PXY MARKET DATA WARNING: Yahoo Finance 1-minute candle "
        f"stale or future-dated; last candle (IST): {candle_time}; "
        f"age: {age} seconds. Engine continues."
    )


def get_all_data():

    # -------- CORE --------
    core = get_full_snapshot() or {}
    _notify_stale_market_data(core)

    # -------- RUN TREND CHART GENERATION FROM THE SAME SNAPSHOT --------
    export_supertrend_json(
        core.get("chart_df", core.get("df"))
    )

    # -------- PRICE LOGIC (DISPLAY/EXECUTION SNAPSHOT ONLY) --------
    # Use the raw NIFTY index price from the market snapshot; no futures blend.
    final_price = core.get("price")

    # Display SMA50 when trading filter is NONE; otherwise show the selected filter.
    # This display fallback does not enable an entry filter.
    filter_mode = "SMA" if SYSMKTPXY_ENTRY_FILTER == "NONE" else SYSMKTPXY_ENTRY_FILTER
    filter_state = "NA"
    filter_df = core.get("df")
    if filter_df is not None and not filter_df.empty:
        try:
            if filter_mode == "SMA":
                filter_state = get_sma_signal(filter_df).get("status", "NA")
            elif filter_mode == "SDIR":
                filter_state = get_structure_direction(filter_df).get("direction", "NA")
        except Exception:
            filter_state = "NA"

    # -------- COMBINE --------
    data = {
        # ===== SYSTEM TIMING =====
        "timestamp": datetime.now(SYSCNFGPXY_TIMEZONE).isoformat(),

        # ===== CORE =====
        "hkin_signal": core.get("hkin_signal", "NONE"),
        "hkin_past_depth": core.get("hkin_past_depth", 0),
        "hkin_ce_depth": core.get("hkin_ce_depth", 1),
        "hkin_pe_depth": core.get("hkin_pe_depth", 1),
        "hkin_signal_time": core.get("hkin_signal_time"),

        "atr": core.get("atr"),
        "katr": core.get("katr"),
        "price": final_price,
        "direction": core.get("direction"),

        "supertrend": core.get("supertrend"),
        "entry_filter": filter_mode,
        "entry_filter_state": filter_state,
        "super_line": core.get("super_line"),
        "sma": core.get("sma", "NA"),
        "tsma": core.get("tsma", "NA"),

        "ce_power": core.get("ce_power"),
        "pe_power": core.get("pe_power"),

        # FORCE FIX (SINGLE ADDITION)
        "ce_force": core.get("ce_force", 1.0),
        "pe_force": core.get("pe_force", 1.0),

        "entry": core.get("entry"),
        "exit": core.get("exit"),
        "market_data_available": core.get(
            "market_data_available", False
        ),

        # ===== NEW =====
        "candle_visual": core.get("candle_visual", ""),
        "bos_bar": core.get("bos_bar", "NONE"),
        "bos_val": core.get("bos_val", "0%"),
        "day_candle": core.get("day_candle", ""),
    }

    # -------- TARGET: pxy/web DIRECTORY --------
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.abspath(
        os.path.join(current_dir, "..", "web")
    )

    # Safeguard: Create web folder if it's missing
    os.makedirs(target_dir, exist_ok=True)

    target_file = os.path.join(
        target_dir,
        "webdashpxy.json"
    )

    # Publish the completed dashboard snapshot atomically.
    temporary_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target_dir,
            prefix=".webdashpxy.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_file = handle.name
            json.dump(data, handle, indent=4)
        os.replace(temporary_file, target_file)
    finally:
        if temporary_file and os.path.exists(temporary_file):
            os.unlink(temporary_file)

    return data


# ===== SELF TEST =====
if __name__ == "__main__":
    data = get_all_data()

    for k, v in data.items():
        print(f"{k:18}: {v}")

