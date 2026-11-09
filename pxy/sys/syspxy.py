
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
from sysdtafpxy import _read_nifty_futures_price
from sysictrpxy import export_supertrend_json
from syscnfgpxy import SYSMKTPXY_ENTRY_FILTER
from syssmapxy import get_sma_signal
from syssdirpxy import get_structure_direction


def _notify_stale_market_data(core):
    """Throttle console-only market-data warnings; no network calls."""
    state_file = Path(__file__).resolve().parent / "exe" / "run" / ".yahoo_freshness_alert.json"
    if not core.get("market_data_stale", False):
        try:
            state_file.unlink(missing_ok=True)
        except OSError:
            pass
        return
    now_epoch = time.time()
    try:
        last_alert = float(json.loads(state_file.read_text()).get("last_alert_epoch", 0))
    except (OSError, ValueError, TypeError):
        last_alert = 0
    if now_epoch - last_alert < SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS:
        return
    print(
        "⚠️ PXY MARKET DATA WARNING: Yahoo Finance 1-minute candle "
        f"stale or future-dated; last candle (IST): {core.get('market_data_timestamp', 'unknown')}; "
        f"age: {core.get('market_data_age_seconds')} seconds. Engine continues."
    )
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"last_alert_epoch": now_epoch}))
        os.replace(tmp, state_file)
    except OSError as error:
        print(f"Warning: Could not persist freshness diagnostic throttle: {error}")


def get_all_data():

    # -------- CORE --------
    core = get_full_snapshot() or {}
    _notify_stale_market_data(core)

    # -------- RUN TREND CHART GENERATION FROM THE SAME SNAPSHOT --------
    export_supertrend_json(
        core.get("chart_df", core.get("df"))
    )

    # -------- PRICE LOGIC (DISPLAY/EXECUTION SNAPSHOT ONLY) --------
    # Reuse the existing timestamp-validated Kotak Futures feed; no new API call.
    # Average Futures and NIFTY index when both exist; otherwise use the available source.
    # This changes only the published price, never the OHLC or indicators.
    futures_price = _read_nifty_futures_price(max_age_seconds=30 * 60)
    index_price = core.get("price") if core.get("market_data_available", False) else None
    try:
        index_price = float(index_price)
        if not math.isfinite(index_price) or index_price <= 0:
            index_price = None
    except (TypeError, ValueError, OverflowError):
        index_price = None
    # Blend both available prices; otherwise use whichever valid source remains.
    if futures_price is not None and index_price is not None:
        final_price = (futures_price + index_price) / 2.0
    else:
        final_price = futures_price if futures_price is not None else index_price

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

