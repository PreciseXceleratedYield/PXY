#!/usr/bin/env python3
# runexlqdpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER, part 4 of 6: liquidation. Squares off everything (exesqrpxy.py -all), waits until
# the broker is flat, locks the final loss into pnl_offset, resets the engine and ends the process.
# Split out of runexacpxy.py (pure move). The breach decision itself stays in runexacpxy._tick.
import os
import sys
import time
import subprocess
from colorama import Fore, Style

from runexiopxy import SQUAREOFF_SCRIPT_PATH
from syscnfgpxy import (
    RUNEXLQDPXY_FLAT_CONFIRM_POLL_SECONDS as FLAT_CONFIRM_POLL_SECONDS,
    RUNEXLQDPXY_FLAT_CONFIRM_TIMEOUT_SECONDS as FLAT_CONFIRM_TIMEOUT_SECONDS,
    RUNEXLQDPXY_SQUAREOFF_TIMEOUT_SECONDS as SQUAREOFF_TIMEOUT_SECONDS,
)
from runexmtpxy import INITIAL_LOSS_FLOOR, compute_totals, _both_empty
from runexstpxy import save_check_state, save_session_state, _find_runlilo_module
from execoolpxy import start_cooldown

# ==================== CONFIG (this file's settings) ====================
# =======================================================================


def broker_positions_flat(client):
    try:
        def _num(v):
            return float(str(v).replace(",", "").strip() or 0)

        res = client.positions()
        if isinstance(res, dict):
            data = res.get("data")
            if isinstance(data, list):
                for pos in data:
                    net_qty = _num(pos.get("net_qty", 0))
                    if net_qty == 0:
                        net_qty = _num(pos.get("flBuyQty", 0)) - _num(pos.get("flSellQty", 0))
                    if abs(net_qty) > 0:
                        return False
                return True
            if "no data" in str(res.get("errMsg", "") or res.get("message", "")).lower():
                return True
        return False
    except Exception:
        return False


def wait_until_flat(client):
    """Poll the broker until flat or timeout, so slow fills don't cause a false 'not flat'."""
    deadline = time.time() + FLAT_CONFIRM_TIMEOUT_SECONDS
    while True:
        if broker_positions_flat(client):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(FLAT_CONFIRM_POLL_SECONDS)


def run_squareoff():
    if not os.path.exists(SQUAREOFF_SCRIPT_PATH):
        print(f"{Fore.RED}❌ Square-off script not found: {SQUAREOFF_SCRIPT_PATH}")
        return False
    python_executable = sys.executable if sys.executable else "python"
    try:
        result = subprocess.run([python_executable, SQUAREOFF_SCRIPT_PATH, "-all"],
                                timeout=SQUAREOFF_TIMEOUT_SECONDS)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"{Fore.RED}❌ Square-off script timed out after {SQUAREOFF_TIMEOUT_SECONDS}s.")
        return False
    except Exception as e:
        print(f"{Fore.RED}❌ Square-off script failed to run: {e}")
        return False


def _refresh_total(client, fallback_total):
    """Re-pull the ledger after the account is flat so the offset includes the square-off fills."""
    try:
        mod = _find_runlilo_module()
        if mod is None:
            import runlilopxy as mod
        o2, c2 = mod.process_lilo_orders(client)     # re-entrancy guard makes the hooks return at once
        if not _both_empty(o2, c2):
            return compute_totals(o2, c2)["total"]
    except SystemExit:
        raise
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Post-flat ledger refresh failed ({e}); using pre-flat total.")
        return fallback_total
    print(f"{Fore.YELLOW}⚠️ Post-flat ledger came back empty; using pre-flat total.")
    return fallback_total


def liquidate_and_exit(client, total_raw_pnl, risk_control_activated=False):
    """Confirmed breach: square off, wait for flat, lock the offset, reset the engine. Always ends the
    process with sys.exit(...). Flat is decided by the broker, not by the script's exit code."""
    run_squareoff()

    if wait_until_flat(client):
        start_cooldown()
        new_total = _refresh_total(client, total_raw_pnl)
        print(f"🧹 {Fore.GREEN}Broker flat verified! Locking offset at ₹{new_total:,.0f} and restarting engine...")
        pnl_offset = new_total
        save_check_state(0)
        save_session_state(
            0.0,
            0.0,
            INITIAL_LOSS_FLOOR,
            pnl_offset,
            risk_control_activated=risk_control_activated,
        )
        sys.exit("Master Circuit Breaker Triggered.")

    print(f"{Fore.RED}⚠️ Broker not flat after {FLAT_CONFIRM_TIMEOUT_SECONDS:.0f}s. "
          f"Keeping breach count; square-off retries next tick.")
    sys.exit("Master Circuit Breaker Triggered (broker not flat yet; square-off retries next tick).")
