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

        # 🎯 STRICT FALLBACK REPLACEMENT: Pull raw market state direction flag directly 
        # (Supports native UP, DOWN, and SIDE values from your core snapshot row data)
        global_exit = (
            str(first_row.get("direction", "NONE")).upper().strip()
        )

        # 🛑 CRITICAL REGIME INTERCEPT BYPASS: If market is sideways, bypass panic liquidation checks.
        # This keeps the portfolio active for standard grid-balancing and dynamic side averaging.
        if global_exit == "SIDE":
            return False

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

        # 🎯 FALLBACK STRUCTURAL MAPPING: Evaluate heavier side criteria matching UP/DOWN keys
        side_condition_met = False
        if ce_count > pe_count:
            # CE is heavier: Trigger exit if global state shifts to DOWN, BEAR, or SELL
            if global_exit in ("DOWN", "BEAR", "SELL"):
                side_condition_met = True
        elif pe_count > ce_count:
            # PE is heavier: Trigger exit if global state shifts to UP, BULL, or BUY
            if global_exit in ("UP", "BULL", "BUY"):
                side_condition_met = True
        else:
            # Even distribution: Trigger if the global flip matches either hostile zone
            if global_exit in ("DOWN", "BEAR", "SELL", "UP", "BULL", "BUY"):
                side_condition_met = True

        # 3️⃣ CRITICAL ACCELERATION MATCH WITH BIAS EXIT GATES
        if (
            active_count >= 3                 # 📊 Catches your 2CE + 1PE footprint cleanly
            and combined_depth < 3            # ⚡ Catches the exact peak momentum orderbook thinness
            and active_pnl_sum >= 140         # 💰 Clear of 139 target floor with slippage protection margin
            and has_both_sides                # 🔒 Validates that dual-hedged layers protect the account
            and side_condition_met            # 🚥 Checks hostile signal mix / trend flip against your heavy leg
        ):

            print(
                f"\n🚨 {Fore.YELLOW}{Style.BRIGHT}TREND COLLAPSE ALIGNED (PRE-AVERAGING)!{Style.RESET_ALL}"
            )
            print(
                f"📊 Rows: {active_count} (CE: {ce_count} | PE: {pe_count}) | Direction Status: {global_exit} | Global PNL: +{active_pnl_sum:.2f}"
            )
            print(
                f"⚠️ Signal Matrix Confirmed: Market State ({global_exit}) matches heavier side risk profile."
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
