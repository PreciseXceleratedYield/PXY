import sys
import os
import subprocess
import traceback
from pathlib import Path
import pandas as pd
from colorama import Fore, Style, init

# --- DYNAMIC PATH SCANNING FOR SYSPXY & RUN SUBDIRECTORY ---
HERE = Path(__file__).resolve().parent

syspxy_path = None
for parent in HERE.parents:
    if (parent / 'syspxy.py').exists() or (parent / 'syspxy.pyc').exists():
        syspxy_path = parent
        break

if syspxy_path:
    sys.path.insert(0, str(syspxy_path))

try:
    import syspxy
except Exception:
    syspxy = None

run_dir = os.path.join(str(HERE), "run")
if run_dir not in sys.path:
    sys.path.append(run_dir)

from runclntpxy import get_session

try:
    import exepmspxy as pms
except ImportError:
    sys.path.insert(0, str(HERE))
    import exepmspxy as pms

init(autoreset=True)

def calculate_target_profit(qty, atr_val):
    """Evaluates your custom formula: Target Points = ATR / (Quantity / 65)"""
    try:
        if qty is None or atr_val is None:
            return None
        numeric_qty = abs(pms.safe_int_convert(qty, 0))
        numeric_atr = pms.safe_float_convert(atr_val, None)
        if numeric_qty == 0 or numeric_atr is None:
            return None
        count_factor = numeric_qty / 65.0
        if count_factor <= 0.0001:
            return None
        target_points = numeric_atr / count_factor
        return target_points, count_factor
    except Exception:
        print(f"{Fore.RED}[DEBUG CRITICAL] Math calculation anomaly inside runner:")
        traceback.print_exc()
        return None

def place_exit_order(client, row, sym_col, qty_col):
    """Assembles parameter structures and fires a 100% volume market square-off order."""
    try:
        symbol = row.get(sym_col)
        qty = pms.safe_int_convert(row.get(qty_col), 0)
        existing_tag = row.get('tag')
        if not symbol or qty == 0:
            return None

        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']:
            base_tag = str(existing_tag).split('_').strip()
        else:
            import pytz
            from datetime import datetime
            base_tag = datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%H%M%S')

        final_tag = f"{base_tag}{pms.get_sell_suffix()}"
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
            "quantity": str(abs(qty)), "validity": "DAY", "trading_symbol": str(symbol),
            "transaction_type": "S", "amo": "NO", "tag": final_tag
        }
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXITING: {symbol} Qty: {qty} | TAG: {final_tag}")
        return client.place_order(**params)
    except Exception:
        print(f"{Fore.RED}[DEBUG CRITICAL] place_exit_order failed execution. Full Traceback:")
        traceback.print_exc()
        return None

def main():
    try:
        client = get_session()
        if not client:
            print(f"{Fore.RED}❌ Broker session authentication failed.")
            return

        active_df = pms.get_positions_df(client)
        if active_df.empty:
            print(f"{Fore.YELLOW}No active positions detected at broker.")
            return

        atr_val, exit_signal = None, "NONE"
        if syspxy is not None and hasattr(syspxy, 'get_all_data'):
            try:
                sys_data = syspxy.get_all_data() or {}
                atr_val = pms.safe_float_convert(sys_data.get("atr"), None)
                exit_raw = sys_data.get("exit")
                if exit_raw and not pd.isna(exit_raw):
                    exit_signal = str(exit_raw).upper().strip()
                print(f"{Fore.BLUE}📊 CONTEXT -> Global ATR: {atr_val} | Global Exit Level: {exit_signal}")
            except Exception:
                print(f"{Fore.RED}[DEBUG CRITICAL] syspxy data extraction failure. Action: DO NOTHING.")
                traceback.print_exc()
                return

        sym_col = "symbol" if "symbol" in active_df.columns else "trading_symbol"
        qty_col = "qty" if "qty" in active_df.columns else ("netqty" if "netqty" in active_df.columns else "quantity")
        token_col = next((c for c in active_df.columns if c.lower() in ['instrument_token', 'token', 'token_id', 'tok', 'asset_token']), None)
        seg_col = next((c for c in active_df.columns if c.lower() in ['exchange_segment', 'segment', 'exchange', 'exseg']), None)
        avg_col = next((c for c in active_df.columns if c.lower() in ['avg_price', 'average_price', 'buy_price', 'netavgprc', 'buy_avg_price', 'prc']), None)

        any_order_placed = False
        for _, row in active_df.iterrows():
            try:
                symbol = str(row.get(sym_col, "")).upper().strip()
                qty = pms.safe_int_convert(row.get(qty_col), 0)
                if not symbol or symbol in ['NAN', 'NONE', ''] or qty == 0:
                    continue

                if ("CE" in symbol and exit_signal in ["BULL", "BUY"]) or ("PE" in symbol and exit_signal in ["BEAR", "SELL"]):
                    print(f"{Fore.CYAN}🛡️ MOMENTUM HOLD: Keeping {symbol} | Signal is {exit_signal}")
                    continue

                if atr_val is None or avg_col is None:
                    print(f"{Fore.RED}[DEBUG ALERT] Core headers missing for {symbol}. Action: DO NOTHING.")
                    continue

                avg_price = pms.safe_float_convert(row.get(avg_col), None)
                live_price = pms.fetch_live_mid_price(client, row, token_col, seg_col)
                if avg_price is None or live_price <= 0.0:
                    print(f"{Fore.RED}[DEBUG ALERT] Pricing lookup failed/zero for {symbol}. Action: DO NOTHING.")
                    continue

                math_result = calculate_target_profit(qty, atr_val)
                if math_result is None:
                    print(f"{Fore.RED}[DEBUG ALERT] Math anomaly generated for {symbol}. Action: DO NOTHING.")
                    continue
                    
                target_profit_points, count = math_result
                points_gained = live_price - avg_price

                if points_gained < target_profit_points:
                    print(f"{Fore.YELLOW}⏳ TARGET NOT MET: Holding {symbol} | Gained: {points_gained:.2f} / Target: {target_profit_points:.2f} (Count: {count:.2f})")
                    continue
                else:
                    print(f"{Fore.GREEN}🎯 TARGET ACHIEVED: {symbol} reached {points_gained:.2f} points (Target: {target_profit_points:.2f})")

                if place_exit_order(client, row, sym_col, qty_col):
                    any_order_placed = True
            except Exception:
                print(f"{Fore.RED}[DEBUG CRITICAL] Row iteration failed for position {row.get(sym_col, 'UNKNOWN')}. Action: DO NOTHING.")
                traceback.print_exc()
                continue

        if any_order_placed:
            try:
                script_path = os.path.join(str(HERE), "sysddmppxy.py")
                if os.path.exists(script_path):
                    subprocess.Popen(["python3", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                print(f"{Fore.RED}[DEBUG CRITICAL] sysddmppxy.py background launch failed.")
                traceback.print_exc()

        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 Risk loop pass completed.")
    except Exception:
        print(f"{Fore.RED}[DEBUG CRITICAL] Master script loop runtime exception. Action: ABORT OPERATION.")
        traceback.print_exc()

if __name__ == "__main__":
    main()
