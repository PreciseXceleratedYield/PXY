#exeexitpxy.py
import sys
import os
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd
from colorama import Fore, Style, init

# --- DYNAMIC UPWARD SYSTEM CONTROLLER PATH SCANNING ---
HERE = Path(__file__).resolve().parent
syspxy_path = next((p for p in HERE.parents if (p / 'syspxy.py').exists() or (p / 'syspxy.pyc').exists()), None)
if syspxy_path: sys.path.insert(0, str(syspxy_path))

try: import syspxy
except Exception: syspxy = None

run_dir = os.path.join(str(HERE), "run")
if run_dir not in sys.path: sys.path.append(run_dir)

from runclntpxy import get_session
try: import exepmspxy as pms
except ImportError: sys.path.insert(0, str(HERE)); import exepmspxy as pms

init(autoreset=True)

def calculate_target_profit(qty, atr_val):
    try:
        if qty is None or atr_val is None: return None
        num_qty, num_atr = abs(pms.safe_int_convert(qty, 0)), pms.safe_float_convert(atr_val, None)
        if num_qty == 0 or num_atr is None: return None
        # Target = ATR / (Qty / 65)
        factor = num_qty / 65.0
        return (num_atr / factor, factor) if factor > 0.0001 else None
    except Exception: return None

def square_off_entire_type(client, active_df, target_type):
    try:
        # Filter down to the matching option side block
        target_rows = active_df[active_df["opt_type"].str.upper().strip() == target_type].copy()
        
        # 🎯 SORTING UPGRADE: Convert PNL to numeric and sort highest profit rows to the top
        if "pnl" in target_rows.columns:
            target_rows["pnl_numeric"] = pd.to_numeric(target_rows["pnl"], errors='coerce').fillna(0.0)
            target_rows = target_rows.sort_values(by="pnl_numeric", ascending=False)
        
        # Loop through row-by-row (now explicitly prioritized by highest profit)
        for _, row in target_rows.iterrows():
            symbol, qty = row.get("symbol"), pms.safe_int_convert(row.get("qty"), 0)
            if not symbol or qty == 0: continue
            
            tag = row.get('tag')
            clean_tag = str(tag).strip()
            
            # Check for invalid configurations to assign a timestamp fallback string cleanly
            if not tag or clean_tag.lower() in ['nan', 'none', '']:
                base_tag = datetime.now().strftime('%H%M%S')
            else:
                base_tag = clean_tag.split('_')[0].strip()
            
            params = {
                "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
                "quantity": str(abs(qty)), "validity": "DAY", "trading_symbol": str(symbol),
                "transaction_type": "S", "amo": "NO", "tag": f"{base_tag}{pms.get_sell_suffix()}"
            }
            row_pnl = row.get('pnl', 0)
            print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ HIGHEST PROFIT FIRST EXIT -> {target_type}: {symbol} Qty: {qty} | PnL: {row_pnl} | Tag: {params['tag']}")
            client.place_order(**params)
        return True
    except Exception: 
        traceback.print_exc()
        return False

def main():
    try:
        client = get_session()
        if not client: return
        atr_val, exit_signal = None, "NONE"
        if syspxy is not None and hasattr(syspxy, 'get_all_data'):
            sys_data = syspxy.get_all_data() or {}
            atr_val = pms.safe_float_convert(sys_data.get("atr"), None)
            exit_raw = sys_data.get("exit")
            if exit_raw and not pd.isna(exit_raw): exit_signal = str(exit_raw).upper().strip()
            print(f"{Fore.BLUE}🪜 ATR Level: {atr_val} |🚥 Exit Level: {exit_signal}")

        active_df = pms.fetch_upstream_active_df()
        summary_df = pms.generate_option_summary(active_df)
        any_order_placed = False
        
        if not summary_df.empty:
            for _, type_row in summary_df.iterrows():
                opt_type = str(type_row.get("SIDE", "")).upper().strip()
                if opt_type == "TOT": continue
                
                total_qty = pms.safe_int_convert(type_row.get("QTY"), 0)
                total_pnl = pms.safe_float_convert(type_row.get("DIFF"), 0.0) # SIDE PNL (as points/%)
                
                if not opt_type or total_qty == 0: continue

                # 🛑 MANDATORY CONDITION: Cumulative Quantity per side MUST be > 66
                if total_qty <= 66:
                    print(f"{Fore.YELLOW}⏳ SIDE IGNORED: {opt_type} quantity ({total_qty}) is not > 66. Skipping logic.")
                    continue

                # 🛡️ TREND PROTECTION CHECK
                if (opt_type == "CE" and exit_signal in ["BULL", "BUY"]) or (opt_type == "PE" and exit_signal in ["BEAR", "SELL"]):
                    print(f"{Fore.CYAN}🛡️ TYPE LEVEL HOLD: Protecting all {opt_type} positions | Signal is {exit_signal}"); continue
                
                if atr_val is None: continue
                
                # 🎯 ACHIEVE EXIT WITH ATR/QTY FACTOR
                math_res = calculate_target_profit(total_qty, atr_val)
                if math_res is None: continue
                target_profit_points, count = math_res
                
                if total_pnl < target_profit_points:
                    print(f"{Fore.YELLOW}⏳ TARGET NOT MET: Holding {opt_type} | PnL: {total_pnl:.2f} / Target: {target_profit_points:.2f}")
                    continue
                else:
                    print(f"{Fore.GREEN}🎯 TARGET ACHIEVED: {opt_type} reached {total_pnl:.2f} points (Target: {target_profit_points:.2f})")
                    if square_off_entire_type(client, active_df, opt_type): 
                        any_order_placed = True

        # Render Dashboard
        pms.print_portfolio_table(active_df, summary_df)
        
        # Trigger Downstream Data Cleanup
        if any_order_placed:
            cleanup_script = os.path.join(str(HERE), "sysddmppxy.py")
            if os.path.exists(cleanup_script):
                subprocess.Popen(["python3", cleanup_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 Risk loop pass completed.")
    except Exception: 
        traceback.print_exc()

if __name__ == "__main__":
    main()
