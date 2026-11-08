#!/usr/bin/env python3
# runexlqdpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER, part 4 of 6: liquidation. Submits square-off orders and returns immediately.
# A later broker snapshot confirms flatness before pnl_offset and risk state are finalized.
# Split out of runexacpxy.py (pure move). The breach decision itself stays in runexacpxy._tick.
import os
import sys
import subprocess
import math
from colorama import Fore, Style

from runexiopxy import SQUAREOFF_SCRIPT_PATH
from syscnfgpxy import (
    RUNEXLQDPXY_SQUAREOFF_TIMEOUT_SECONDS as SQUAREOFF_TIMEOUT_SECONDS,
)
from runexmtpxy import (
    INITIAL_RISK_BAR_TARGET, compute_totals, cycle_closed_snapshot,
    _both_empty,
)
from runexstpxy import (
    save_check_state, save_session_state, _find_runlilo_module,
)
from execoolpxy import start_cooldown

# ==================== CONFIG (this file's settings) ====================
# =======================================================================


def broker_positions_flat(client):
    """Return True only for a successful, complete broker response showing flat.

    Use the same carry-forward + intraday quantity interpretation as LILO.
    Missing, malformed, unsuccessful, or incomplete responses are never flat.
    """
    try:
        res = client.positions()

        # A valid empty data list is an explicit flat result. Error/no-data
        # payloads are not accepted as proof because they may hide API failure.
        if (
            not isinstance(res, dict)
            or str(res.get("stat", "")).strip().lower() != "ok"
            or str(res.get("stCode", "")).strip() != "200"
            or not isinstance(res.get("data"), list)
        ):
            return False

        from runlilopxy import position_net_quantity

        net_by_symbol = {}
        for pos in res["data"]:
            if not isinstance(pos, dict):
                return False

            symbol = str(pos.get("trdSym") or "").strip()
            if not symbol:
                return False

            try:
                net_qty = position_net_quantity(pos)
            except (TypeError, ValueError, OverflowError):
                return False

            if not math.isfinite(net_qty):
                return False

            net_by_symbol[symbol] = net_by_symbol.get(symbol, 0.0) + net_qty

        return all(abs(quantity) <= 1e-9 for quantity in net_by_symbol.values())

    except Exception:
        # An unavailable broker response must keep the cycle open and trigger
        # another square-off/confirmation attempt on the next risk-ledger tick.
        return False


def has_working_sell_orders(client, symbols=None, order_report=None):
    """Prevent duplicate sells; optionally use one pre-fetched broker order snapshot."""
    if order_report is None:
        try:
            try:
                response = client.order_report()
            except AttributeError:
                response = client.orders()
        except Exception as error:
            print(f"{Fore.YELLOW}⚠️ Cannot verify working sell orders; duplicate square-off blocked: {error}")
            return True
    else:
        response = order_report

    if (
        isinstance(response, dict)
        and str(response.get("stat", "")).strip().lower() in {"not_ok", "not ok"}
        and str(response.get("stCode", "")).strip() == "5203"
        and str(response.get("errMsg", "")).strip().lower() == "no data"
    ):
        return False

    if (
        not isinstance(response, dict)
        or str(response.get("stat", "")).strip().lower() != "ok"
        or str(response.get("stCode", "")).strip() != "200"
        or not isinstance(response.get("data"), list)
    ):
        print(f"{Fore.YELLOW}⚠️ Invalid order report; duplicate square-off blocked.")
        return True

    symbol_filter = {
        str(symbol).strip().upper()
        for symbol in (symbols or [])
        if str(symbol).strip()
    }
    active_statuses = {
        "working", "open", "validation pending", "pending",
        "trigger pending", "open pending",
    }
    for order in response["data"]:
        if not isinstance(order, dict):
            continue
        status = str(order.get("ordSt", order.get("status", ""))).strip().lower()
        if status not in active_statuses:
            continue
        side = str(order.get("trnsTp", order.get("side", ""))).strip().upper()
        if side not in {"S", "SELL"}:
            continue
        symbol = str(order.get("trdSym", order.get("trading_symbol", ""))).strip().upper()
        if not symbol_filter or symbol in symbol_filter:
            print(
                f"{Fore.YELLOW}⏳ Existing sell order still working for {symbol or 'unknown symbol'}; "
                "waiting for the next broker snapshot."
            )
            return True
    return False


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
            return compute_totals(o2, c2)["total"], c2
    except SystemExit:
        raise
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Post-flat ledger refresh failed ({e}); using pre-flat total.")
        return fallback_total, None
    print(f"{Fore.YELLOW}⚠️ Post-flat ledger came back empty; using pre-flat total.")
    return fallback_total, None


def liquidate_and_exit(
    client, total_raw_pnl, risk_control_activated=False, risk_state=None,
    broker_flat_confirmed=False,
):
    """Submit liquidation and return; finalize only after a later broker snapshot is flat."""
    state = dict(risk_state or {})
    if not broker_flat_confirmed:
        if has_working_sell_orders(client, state.get("open_symbols", [])):
            return False
        if not run_squareoff():
            print(f"{Fore.RED}⚠️ Square-off submission did not complete; liquidation remains pending.")
        else:
            print(f"{Fore.YELLOW}📤 Square-off submitted. Awaiting the next broker snapshot; no fill wait.")
        return False

    start_cooldown()
    new_total, closed_df = _refresh_total(client, total_raw_pnl)
    print(
        f"🧹 {Fore.GREEN}Broker flat verified! Locking offset at ₹{new_total:,.0f} "
        "and finalizing the risk reset..."
    )
    cycle_tags = {str(tag) for tag in state.get("cycle_tags", [])}
    cycle_started_at = state.get("cycle_started_at")
    cycle_id = (
        f"{cycle_started_at}|{'|'.join(sorted(cycle_tags))}"
        if cycle_started_at and cycle_tags else ""
    )
    snapshot = cycle_closed_snapshot(
        closed_df, cycle_tags, cycle_started_at
    )
    if snapshot is not None and cycle_id != state.get("last_closed_cycle_id"):
        state["booked_profit"] = (
            float(state.get("booked_profit", 0.0))
            + snapshot["realized_pnl"]
        )
        state["closed_cycle_count"] = (
            int(state.get("closed_cycle_count", 0)) + 1
        )
        snapshot["cycle_id"] = state["closed_cycle_count"]
        state["last_closed_snapshot"] = snapshot
        state["last_closed_cycle_id"] = cycle_id
        state["closed_cycles"] = [
            *state.get("closed_cycles", []),
            snapshot,
        ]

    target_line = INITIAL_RISK_BAR_TARGET
    save_check_state(0)
    state_saved = save_session_state(
        0.0,
        0.0,
        -target_line,
        new_total,
        risk_control_activated=risk_control_activated,
        target_exit_line=target_line,
        booked_profit=state.get("booked_profit", 0.0),
        closed_cycle_count=state.get("closed_cycle_count", 0),
        last_closed_snapshot=state.get("last_closed_snapshot"),
        last_closed_cycle_id=state.get("last_closed_cycle_id", ""),
        closed_cycles=state.get("closed_cycles", []),
        active_cycle_id=None,
        active_cycle_tags=[],
        active_cycle_started_at=None,
        liquidation_pending=False,
    )
    if not state_saved:
        print(f"{Fore.RED}⚠️ Could not persist completed liquidation state; pending flag retained.")
        return False

    print(f"{Fore.GREEN}✅ Master risk liquidation confirmed flat; risk state reset.")
    return True
