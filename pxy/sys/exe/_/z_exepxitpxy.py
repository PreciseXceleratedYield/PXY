import sys
import os
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd
from colorama import Fore, Style, init
from syscnfgpxy import (
    EXEEXITPXY_ORDER_AMO,
    EXEEXITPXY_ORDER_EXCHANGE_SEGMENT,
    EXEEXITPXY_ORDER_PRICE,
    EXEEXITPXY_ORDER_PRODUCT,
    EXEEXITPXY_ORDER_TRANSACTION_TYPE,
    EXEEXITPXY_ORDER_TYPE,
    EXEEXITPXY_ORDER_VALIDITY,
    SYSCNFGPXY_TIMEZONE,
)

# --- DYNAMIC PATH SCANNING ---
HERE = Path(__file__).resolve().parent

# Fix: Dynamically find and inject the 'run' folder for runclntpxy
run_dir = HERE / 'run'
if run_dir.exists() and str(run_dir) not in sys.path:
    sys.path.insert(0, str(run_dir))

syspxy_path = next((p for p in HERE.parents if (p / 'syspxy.py').exists() or (p / 'syspxy.pyc').exists()), None)
if syspxy_path:
    sys.path.insert(0, str(syspxy_path))

try:
    import syspxy
except Exception:
    syspxy = None

# Fix: Safely fallback for exepmspxy path context
try:
    import exepmspxy as pms
except ImportError:
    sys.path.insert(0, str(HERE)); import exepmspxy as pms

# Now that path injection is configured correctly, import runclntpxy
from runclntpxy import get_session

init(autoreset=True)

def calculate_target_percentage(qty, atr_val):
    """
    Calculates target threshold as a percentage.
    Example: ATR = 6, factor = 2 -> Target = 3%
    """
    try:
        if qty is None or atr_val is None:
            return None
        
        num_qty = abs(pms.safe_int_convert(qty, 0))
        num_atr = pms.safe_float_convert(atr_val, None)
        
        if num_qty == 0 or num_atr is None:
            return None
        
        # Adjust this formula denominator based on how your quantity factor scales
        factor = num_qty / 32.5  # Yields 2 if quantity is 65
        
        if factor > 0.0001:
            target_pct = num_atr / factor  # e.g., 6 / 2 = 3.0 (%)
            return (target_pct, factor)
        return None
    except Exception:
        return None

def square_off_entire_type(client, active_df, target_type):
    try:
        target_rows = active_df[active_df["opt_type"].str.upper().strip() == target_type].copy()
        if "pnl" in target_rows.columns:
            target_rows["pnl_numeric"] = pd.to_numeric(target_rows["pnl"], errors='coerce').fillna(0.0)
        target_rows = target_rows.sort_values(by="pnl_numeric", ascending=False)
        
        for _, row in target_rows.iterrows():
            symbol, qty = row.get("symbol"), pms.safe_int_convert(row.get("qty"), 0)
            if not symbol or qty == 0:
                continue
            
            tag = row.get('tag')
            if tag and str(tag).lower() not in ['nan', 'none', '']:
                base_tag = str(tag).split('_')[0].strip()
            else:
                base_tag = datetime.now(SYSCNFGPXY_TIMEZONE).strftime('%H%M%S')
            
            params = {
                "exchange_segment": EXEEXITPXY_ORDER_EXCHANGE_SEGMENT,
                "product": EXEEXITPXY_ORDER_PRODUCT,
                "price": EXEEXITPXY_ORDER_PRICE,
                "order_type": EXEEXITPXY_ORDER_TYPE,
                "quantity": str(abs(qty)),
                "validity": EXEEXITPXY_ORDER_VALIDITY,
                "trading_symbol": str(symbol),
                "transaction_type": EXEEXITPXY_ORDER_TRANSACTION_TYPE,
                "amo": EXEEXITPXY_ORDER_AMO,
                "tag": f"{base_tag}{pms.get_sell_suffix()}"
            }
            print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXIT -> {target_type}: {symbol} | Qty: {qty} | PnL: {row.get('pnl')}")
            client.place_order(**params)
        return True
    except Exception:
        return False

def main():
    try:
        client = get_session()
        if not client:
            return

        atr_val, exit_signal = None, "NONE"
        if syspxy and hasattr(syspxy, 'get_all_data'):
            sys_data = syspxy.get_all_data() or {}
            atr_val = pms.safe_float_convert(sys_data.get("atr"), None)
            exit_raw = sys_data.get("exit")
            if exit_raw and not pd.isna(exit_raw):
                exit_signal = str(exit_raw).upper().strip()
                
        print(f"{Fore.BLUE}🪜 ATR Level: {atr_val} |🚥 Exit Level: {exit_signal}")

        active_df = pms.fetch_upstream_active_df()
        summary_df = pms.generate_option_summary(active_df)
        any_order_placed = False

        if not summary_df.empty:
            for _, type_row in summary_df.iterrows():
                opt_type = str(type_row.get("SIDE", "")).upper().strip()
                if opt_type == "TOT":
                    continue
                
                total_qty = pms.safe_int_convert(type_row.get("QTY"), 0)
                total_pnl = pms.safe_float_convert(type_row.get("DIFF"), 0.0)
                
                # --- PERCENTAGE EXTRACTION ---
                # Ensure you are fetching or calculating your active percentage return here
                # Example: total_pnl_pct = (total_pnl / investment_cost) * 100
                total_pnl_pct = pms.safe_float_convert(type_row.get("PNL_PCT"), 0.0) 

                if not opt_type or total_qty == 0:
                    continue

                if total_qty <= 66:
                    print(f"{Fore.YELLOW}⏳ SIDE IGNORED: {opt_type} quantity ({total_qty}) not > 66.")
                    continue

                if (opt_type == "CE" and exit_signal in ["BULL", "BUY"]) or (opt_type == "PE" and exit_signal in ["BEAR", "SELL"]):
                    print(f"{Fore.CYAN}🛡️ TYPE HOLD: {opt_type} Trend matches signal {exit_signal}")
                    continue

                if atr_val is None:
                    continue

                math_res = calculate_target_percentage(total_qty, atr_val)
                if math_res is None:
                    continue

                target_profit_pct, count = math_res

                # Comparing actual % return vs your calculated ATR % threshold
                if total_pnl_pct < target_profit_pct:
                    print(f"{Fore.YELLOW}⏳ {opt_type} PnL %: {total_pnl_pct:.2f}% / Target: {target_profit_pct:.2f}%")
                else:
                    print(f"{Fore.GREEN}🎯 TARGET ACHIEVED: {opt_type} bulk exit triggered at {total_pnl_pct:.2f}%.")
                    if square_off_entire_type(client, active_df, opt_type):
                        any_order_placed = True

        pms.print_portfolio_table(active_df, summary_df)

        if any_order_placed:
            subprocess.Popen(["python3", str(HERE.parent / "sysddmppxy.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 Risk pass done.")

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    main()
