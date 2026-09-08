# exerskmgtpxy.py
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
        active_pnl_sum = pd.to_numeric(df['pnl'], errors='coerce').fillna(0).sum()
        if active_pnl_sum <= 0:
            return False  # Exit immediately if total PNL is not positive or flat

        # 2️⃣ SECONDARY CONDITIONS: Only checked if PNL > 0
        active_count = len(df)
        first_row = df.iloc[0]
        ce_depth = int(pd.to_numeric(first_row.get("hkin_ce_depth", 0), errors='coerce') or 0)
        pe_depth = int(pd.to_numeric(first_row.get("hkin_pe_depth", 0), errors='coerce') or 0)
        combined_depth = ce_depth + pe_depth

        # 3️⃣ CRITICAL ACCELERATION MATCH
        if active_count > 5 and combined_depth < 3:
            print(f"\n🚨 {Fore.YELLOW}{Style.BRIGHT}TREND COLLAPSE ALIGNED (PRE-AVERAGING)!{Style.RESET_ALL}")
            print(f"📊 Rows: {active_count} | Global PNL: +{active_pnl_sum:.2f} | Combined Depth: {combined_depth}")
            print(f"{Fore.RED}🚀 Executing Master Square-Off Engine via external script...{Style.RESET_ALL}\n")
            
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exesqrpxy.py")
            if os.path.exists(exe_path):
                print(f"{Fore.RED}🚀 Executing Master Square-Off Engine via Risk Management module (exerskmgtpxy.py)...{Style.RESET_ALL}\n")
                subprocess.run(["python3", exe_path, "-all"], check=True)
                return True  # Signal that a global square-off occurred
    except Exception as e:
        print(f"⚠️ Error inside external trend collapse evaluation: {e}")
    return False
