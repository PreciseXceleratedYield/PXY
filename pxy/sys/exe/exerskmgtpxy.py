# =============================================================================
# ENGINE COMPONENT MODULE: exerskmgtpxy.py
# PORTFOLIO LEVEL TREND COLLAPSE DETECTION & EMERGENCY EXIT ENGINE
# =============================================================================
import os
import subprocess
import pandas as pd
from colorama import Fore, Style


def check_trend_collapse_exit(df, client):
    """🎯 EXTERNAL MODULE: Monitors portfolio state and triggers global exit before side averaging."""
    if df is None or df.empty or client is None:
        return False

    try:
        # 1️⃣ FIRST GATEWAY: Calculate global PNL immediately
        active_pnl_sum = (
            pd.to_numeric(df["pnl"], errors="coerce").fillna(0).sum()
        )
        if active_pnl_sum <= 0:
            return False  # Exit immediately if total PNL is not positive or flat

        # 2️⃣ SECONDARY CONDITIONS: Only checked if PNL > 0
        active_count = len(df)
        first_row = df.iloc[0]

        ce_depth = int(
            pd.to_numeric(first_row.get("hkin_ce_depth", 0), errors="coerce")
            or 0
        )
        pe_depth = int(
            pd.to_numeric(first_row.get("hkin_pe_depth", 0), errors="coerce")
            or 0
        )
        combined_depth = ce_depth + pe_depth

        # 🔍 STRICT HEDGING & HEAVY-SIDE ANALYSIS
        symbols_upper = (
            df["symbol"].astype(str).str.upper()
            if "symbol" in df.columns
            else pd.Series(dtype=str)
        )
        is_ce_mask = symbols_upper.str.contains("CE")
        is_pe_mask = symbols_upper.str.contains("PE")

        has_ce = is_ce_mask.any()
        has_pe = is_pe_mask.any()
        has_both_sides = has_ce and has_pe

        # Count frequencies to find the heavier side
        ce_count = is_ce_mask.sum()
        pe_count = is_pe_mask.sum()

        # Extract the uniform global exit signal from the first row
        global_exit = (
            str(first_row.get("exit", "NONE")).upper().strip()
        )

        # Evaluate heavier side criteria against the uniform global exit state
        side_condition_met = False
        if ce_count > pe_count:
            # CE is heavier: Trigger exit if global state shifts to BEAR / SELL
            if global_exit in ("SELL", "BEAR"):
                side_condition_met = True
        elif pe_count > ce_count:
            # PE is heavier: Trigger exit if global state shifts to BULL / BUY
            if global_exit in ("BUY", "BULL"):
                side_condition_met = True
        else:
            # Even distribution: Trigger if the global exit matches EITHER hostile zone
            if global_exit in ("SELL", "BEAR", "BUY", "BULL"):
                side_condition_met = True

        # 3️⃣ CRITICAL ACCELERATION MATCH WITH BIAS EXIT GATES
        if (
            active_count > 2
            and combined_depth < 3
            and active_pnl_sum > (active_count * 500)
            and has_both_sides
            and side_condition_met
        ):

            print(
                f"\n🚨 {Fore.YELLOW}{Style.BRIGHT}TREND COLLAPSE ALIGNED (PRE-AVERAGING)!{Style.RESET_ALL}"
            )
            print(
                f"📊 Rows: {active_count} (CE: {ce_count} | PE: {pe_count}) | Global PNL: +{active_pnl_sum:.2f}"
            )
            print(
                f"⚠️ Signal Matrix Confirmed: Global Exit ({global_exit}) matches heavier side risk profile."
            )

            exe_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "exesqrpxy.py"
            )
            if os.path.exists(exe_path):
                print(
                    f"{Fore.RED}🚀 Executing Master Square-Off Engine via Risk Management module (exerskmgtpxy.py)...{Style.RESET_ALL}\n"
                )
                subprocess.run(["python3", exe_path, "-all"], check=True)
                return True  # Signal that a global square-off occurred

    except Exception as e:
        print(f"⚠️ Error inside external trend collapse evaluation: {e}")

    return False

