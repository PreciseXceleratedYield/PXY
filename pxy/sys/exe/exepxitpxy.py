import sys
import os
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
import pandas as pd
from colorama import Fore, Style, init

# --- DYNAMIC PATH SCANNING ---
HERE = Path(__file__).resolve().parent
syspxy_path = next((p for p in HERE.parents if (p / 'syspxy.py').exists() or (p / 'syspxy.pyc').exists()), None)
if syspxy_path: sys.path.insert(0, str(syspxy_path))

try: import syspxy
except Exception: syspxy = None

from runclntpxy import get_session
try: import exepmspxy as pms
except ImportError: sys.path.insert(0, str(HERE)); import exepmspxy as pms

init(autoreset=True)

def calculate_target_profit(qty, atr_val):
    try:
        if qty is None or atr_val is None: return None
        num_qty, num_atr = abs(pms.safe_int_convert(qty, 0)), pms.safe_float_convert(atr_val, None)
        if num_qty == 0 or num_atr is None: return None
        factor = num_qty / 65.0
        return (num_atr / factor, factor) if factor > 0.0001 else None
    except Exception: return None

def square_off_entire_type(client, active_df, target_type):
    try:
        target_rows = active_df[active_df["opt_type"].str.upper().strip() == target_type].copy()
        if "pnl" in target_rows.columns:
            target_rows["pnl_numeric"] = pd.to_numeric(target_rows["pnl"], errors='coerce').fillna(0.0)
            target_rows = target_rows.sort_values(by="pnl_numeric", ascending=False)
        
        for _, row in target_rows.iterrows():
            symbol, qty = row.get("symbol"), pms.safe_int_convert(row.get("qty"), 0)
            if not symbol or qty == 0: continue
            tag = row.get('tag')
            base_tag = str(tag).split('_')[0].strip() if tag and str(tag).lower() not in ['nan', 'none', ''] else datetime.now().strftime('%H%M%S')
            
            params = {
                "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
                "quantity": str(abs(qty)), "validity": "DAY", "trading_symbol": str(symbol),
                "transaction_type": "S", "amo": "NO", "tag": f"{base_tag}{pms.get_sell_suffix()}"
            }
            print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXIT -> {target_type}: {symbol} | Qty: {qty} | PnL: {row.get('pnl')}")
            client.place_order(**params)
        return True
    except Exception: return False

def main():
    try:
        client = get_session()
        if not client: return
        atr_val, exit_signal = None, "NONE"
        if syspxy and hasattr(syspxy, 'get_all_data'):
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
                total_pnl = pms.safe_float_convert(type_row.get("DIFF"), 0.0)
                
                if not opt_type or total_qty == 0: continue

                # ✅ CONDITION: Order ONLY if total cumulative quantity > 66
                if total_qty <= 66:
                    print(f"{Fore.YELLOW}⏳ SIDE IGNORED: {opt_type} quantity ({total_qty}) not > 66.")
                    continue

                if (opt_type == "CE" and exit_signal in ["BULL", "BUY"]) or (opt_type == "PE" and exit_signal in ["BEAR", "SELL"]):
                    print(f"{Fore.CYAN}🛡️ TYPE HOLD: {opt_type} Trend matches signal {exit_signal}"); continue
                
                if atr_val is None: continue
                
                math_res = calculate_target_profit(total_qty, atr_val)
                if math_res is None: continue
                target_profit_points, count = math_res
                
                if total_pnl < target_profit_points:
                    print(f"{Fore.YELLOW}⏳ TARGET NOT MET: {opt_type} PnL: {total_pnl:.2f} / Target: {target_profit_points:.2f}")
                else:
                    print(f"{Fore.GREEN}🎯 TARGET ACHIEVED: {opt_type} bulk exit triggered.")
                    if square_off_entire_type(client, active_df, opt_type): any_order_placed = True

        pms.print_portfolio_table(active_df, summary_df)
        if any_order_placed:
            subprocess.Popen(["python3", str(HERE.parent / "sysddmppxy.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 Risk pass done.")
    except Exception: traceback.print_exc()

if __name__ == "__main__":
    main()

