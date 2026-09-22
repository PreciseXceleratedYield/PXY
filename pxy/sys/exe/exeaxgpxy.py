"""
=============================================================================
PIPELINE FIRING ENGINE: exeaxgpxy.py (axg)
TARGET RESOLUTION ARBITRATOR & SYSTEM-SHELL SCRIPTS TRIGGER PIPELINE
=============================================================================
"""
import os
import logging
from colorama import Fore, Style
from exeamspxy import decide  # 🎯 Pointed explicitly to the new executor file
from exeacgpxy import safe_float, side_overall_pnl_pct, is_cooling, set_cooling

logger = logging.getLogger("exeavgpxy.exeaxgpxy")

def pxysqrce():
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 TARGET HIT: Firing shell script command 'pxysqrce'...")
    try: os.system("pxysqrce")
    except Exception as e: print(f"{Fore.RED}⚠️ Failed to execute system command pxysqrce: {e}")

def pxysqrpe():
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 TARGET HIT: Firing shell script command 'pxysqrpe'...")
    try: os.system("pxysqrpe")
    except Exception as e: print(f"{Fore.RED}⚠️ Failed to execute system command pxysqrpe: {e}")

def pxybuyce():
    print(f"{Fore.GREEN}{Style.BRIGHT}🟢 FRESH ENTRY: Firing shell script command 'pxybuyce'...")
    try: os.system("pxybuyce")
    except Exception as e: print(f"{Fore.RED}⚠️ Failed to execute system command pxybuyce: {e}")

def pxybuype():
    print(f"{Fore.GREEN}{Style.BRIGHT}🟢 FRESH ENTRY: Firing shell script command 'pxybuype'...")
    try: os.system("pxybuype")
    except Exception as e: print(f"{Fore.RED}⚠️ Failed to execute system command pxybuype: {e}")


def _points_profit(rows):
    if rows is None or rows.empty:
        return 0.0
    return float(
        ((rows['sell_prc'].apply(safe_float) - rows['buy_prc'].apply(safe_float))
         * rows['qty'].apply(safe_float)).sum()
    )


def _fire(side, decision):
    """Fires the shell wrapper for a non-hold decision, gated by a System-B-only
    cooldown so a fill/feed lag can't cause the same action to double-fire."""
    if decision == "hold":
        return

    cool_key = f"{side}_TGT"
    if is_cooling(cool_key):
        return

    if decision == "square_off":
        set_cooling(cool_key)
        (pxysqrce if side == "CE" else pxysqrpe)()
    elif decision == "fresh_buy":
        set_cooling(cool_key)
        (pxybuyce if side == "CE" else pxybuype)()


def run_target_engine(active_exit, ce_rows, pe_rows, ce_avg_profit, pe_avg_profit,
                       ce_lots, pe_lots):
    """Gauges metrics pools, filters parameters, and executes terminal actions."""
    ce_empty = ce_rows is None or ce_rows.empty
    pe_empty = pe_rows is None or pe_rows.empty

    ce_points = _points_profit(ce_rows)
    pe_points = _points_profit(pe_rows)

    ce_net = side_overall_pnl_pct(ce_rows)
    pe_net = side_overall_pnl_pct(pe_rows)

    # 🎯 Passing data frame allocations down directly to satisfy the routing matrix wrapper
    ce_decision, ce_aligned = decide(
        "CE", active_exit, ce_avg_profit, ce_points, ce_lots, ce_empty, pe_empty,
        pe_net, pe_points, pe_lots, ce_rows, pe_rows
    )
    pe_decision, pe_aligned = decide(
        "PE", active_exit, pe_avg_profit, pe_points, pe_lots, pe_empty, ce_empty,
        ce_net, ce_points, ce_lots, ce_rows, pe_rows
    )

    _fire("CE", ce_decision)
    _fire("PE", pe_decision)

    return {
        "CE": (ce_decision, ce_aligned, ce_points),
        "PE": (pe_decision, pe_aligned, pe_points),
    }

