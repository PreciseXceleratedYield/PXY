# =============================================================================
# PIPELINE EXECUTION MODULE: exefirpxy.py
# SYSTEM B TARGET SHIELD ROUTER & OS NATIVE TERMINAL CONTROLLER
# =============================================================================
import os
import logging
from colorama import Fore, Style
from exeagtpxy import decide
from exehvgpxy import safe_float

logger = logging.getLogger("exeavgpxy.exefirpxy")

# -----------------------------------------------------------------------------
# 🛠️ UTILITY ACTIONS (SHELL ROUTING LOGIC INTEGRATED CLEANLY)
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# 📈 CORE PIPELINE MATRIX MANAGEMENT
# -----------------------------------------------------------------------------
def _points_profit(rows):
    if rows is None or rows.empty:
        return 0.0
    return float(
        ((rows['sell_prc'].apply(safe_float) - rows['buy_prc'].apply(safe_float))
         * rows['qty'].apply(safe_float)).sum()
    )


def _fire(side, decision):
    if decision == "square_off":
        (pxysqrce if side == "CE" else pxysqrpe)()
    elif decision == "fresh_buy":
        (pxybuyce if side == "CE" else pxybuype)()


def run_target_engine(active_exit, ce_rows, pe_rows, ce_avg_profit, pe_avg_profit,
                       ce_lots, pe_lots):
    """Gauges metrics pools, filters parameters, and executes terminal actions."""
    ce_empty = ce_rows is None or ce_rows.empty
    pe_empty = pe_rows is None or pe_rows.empty

    ce_points = _points_profit(ce_rows)
    pe_points = _points_profit(pe_rows)

    from exehvgpxy import side_overall_pnl_pct
    ce_net = side_overall_pnl_pct(ce_rows)
    pe_net = side_overall_pnl_pct(pe_rows)

    # Route decision tracking via unified strategy brain layout
    ce_decision, ce_aligned = decide(
        "CE", active_exit, ce_avg_profit, ce_points, ce_lots, ce_empty, pe_empty,
        pe_net, pe_points, pe_lots
    )
    pe_decision, pe_aligned = decide(
        "PE", active_exit, pe_avg_profit, pe_points, pe_lots, pe_empty, ce_empty,
        ce_net, ce_points, ce_lots
    )

    # Strict Either/Or Exit Filter Shield Execution Block
    if ce_decision == "square_off" and pe_decision == "fresh_buy":
        pe_decision = "hold"
    if pe_decision == "square_off" and ce_decision == "fresh_buy":
        ce_decision = "hold"

    _fire("CE", ce_decision)
    _fire("PE", pe_decision)

    return {
        "CE": (ce_decision, ce_aligned, ce_points),
        "PE": (pe_decision, pe_aligned, pe_points),
    }
