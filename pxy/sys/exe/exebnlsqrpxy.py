#!/usr/bin/env python3
"""15:15 IST CE/PE worth balance check; exit both sides only when balanced."""
import json
import math
import os
import sys
from datetime import datetime, time as dt_time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYS_DIR = HERE.parent
for folder in (str(HERE), str(HERE / "run"), str(SYS_DIR)):
    if folder not in sys.path:
        sys.path.insert(0, folder)

from syscnfgpxy import SYSCNFGPXY_TIMEZONE, SYSCNFGPXY_SQUAREOFF_START
from exeomspxy import get_combined_data
from execoolpxy import liquidation_pending
from runexlckpxy import ledger_busy

CHECK_START = dt_time(15, 15)
MAX_VARIATION_PCT = 15.0
STATE_FILE = HERE / ".bnlsqrpxy_state.json"


def worths(active):
    if active is None or active.empty:
        raise ValueError("no active positions")
    required = {"symbol", "qty", "sell_prc"}
    if not required.issubset(active.columns):
        raise ValueError("missing required position/valuation fields")
    totals = {"CE": 0.0, "PE": 0.0}
    for _, row in active.iterrows():
        symbol = str(row["symbol"]).upper().strip()
        side = symbol[-2:]
        if side not in totals:
            continue
        qty, price = float(row["qty"]), float(row["sell_prc"])
        if not all(math.isfinite(v) for v in (qty, price)) or qty <= 0 or price <= 0:
            raise ValueError(f"unverified market worth for {symbol}")
        totals[side] += qty * price
    if not all(v > 0 for v in totals.values()):
        raise ValueError("both CE and PE positions required")
    return totals["CE"], totals["PE"]


def main():
    now = datetime.now(SYSCNFGPXY_TIMEZONE)
    if not CHECK_START <= now.time() < SYSCNFGPXY_SQUAREOFF_START:
        return 0
    today = now.date().isoformat()
    try:
        if STATE_FILE.exists() and json.loads(STATE_FILE.read_text()).get("date") == today:
            return 0
    except (OSError, ValueError, TypeError):
        pass
    if liquidation_pending() or ledger_busy():
        print("⚠️ 15:15 balance square-off deferred: liquidation/ledger lock active.")
        return 0
    try:
        data = get_combined_data()
        if data.get("error") or data.get("positions_unverified", True):
            raise ValueError("broker positions/OMS snapshot unverified")
        ce, pe = worths(data.get("active_orders"))
        variation = abs(ce - pe) / ((ce + pe) / 2.0) * 100.0
        print(f"⚖️ 15:15 CE worth ₹{ce:,.2f} | PE worth ₹{pe:,.2f} | variation {variation:.2f}%")
        if variation > MAX_VARIATION_PCT:
            print(f"⚠️ Worth imbalance exceeds ±{MAX_VARIATION_PCT:g}%: warning only; no early square-off.")
            STATE_FILE.write_text(json.dumps({"date": today, "status": "warning", "variation_pct": variation}))
            return 0
        print(f"Not prepared for CAS, i am exiting ⚖️ {variation:.2f}%")
        # Persist before submitting orders to prevent duplicate early square-off on subsequent cycles.
        STATE_FILE.write_text(json.dumps({"date": today, "status": "attempted", "variation_pct": variation}))
        from exesqrpxy import exit_all_positions
        accepted = exit_all_positions(
            "-all", return_accepted_keys=True, check_working_sells=True
        )
        print(f"⚖️ Early balanced square-off accepted rows: {len(accepted or [])}; scheduled 15:30 protection remains.")
    except (ValueError, TypeError, KeyError, OSError) as error:
        print(f"⚠️ 15:15 balance check unavailable: {error}; no early square-off.")
    except Exception as error:
        print(f"⚠️ 15:15 balance square-off failed: {error}; scheduled 15:30 protection remains.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
