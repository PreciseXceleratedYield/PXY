import sys
import os
import subprocess
import traceback
from pathlib import Path
import pandas as pd
from colorama import Fore, Style, init

# --- DYNAMIC PATH SCANNING FOR SYSPXY & RUN SUBDIRECTORY ---
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
        factor = num_qty / 65.0
        return (num_atr / factor, factor) if factor > 0.0001 else None
    except Exception:
        print(f"{Fore.RED}[DEBUG CRITICAL] Math exception:"); traceback.print_exc(); return None

def place_exit_order(client, row, sym_col, qty_col):
    try:
        symbol, qty = row.get(sym_col), pms.safe_int_convert(row.get(qty_col), 0)
        if not symbol or qty == 0: return None
        tag = row.get('tag')
        base_tag = str(tag).split('_')[0].strip() if tag and str(tag).lower() not in ['nan', 'none', ''] else datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%H%M%S')
        final_tag = f"{base_tag}{pms.get_sell_suffix()}"
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
            "quantity": str(abs(qty)), "validity": "DAY", "trading_symbol": str(symbol),
            "transaction_type": "S", "amo": "NO", "tag": final_tag
        }
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXITING: {symbol} Qty: {qty} | TAG: {final_tag}")
        return client.place_order(**params)
    except Exception:
        print(f"{Fore.RED}[DEBUG CRITICAL] Order failed:"); traceback.print_exc(); return None

def main():
    try:
        client = get_session()
        if not client: print(f"{Fore.RED}❌ Broker session failed."); return
        atr_val, exit_signal = None, "NONE"
        if syspxy is not None and hasattr(syspxy, 'get_all_data'):
            try:
                sys_data = syspxy.get_all_data() or {}
                atr_val = pms.safe_float_convert(sys_data.get("atr"), None)
                exit_raw = sys_data.get("exit")
                if exit_raw and not pd.isna(exit_raw): exit_signal = str(exit_raw).upper().strip()
                print(f"{Fore.YELLOW}🪜 ATR Level: {atr_val} | ⚡⚡ Exit Level: {exit_signal}")
            except Exception:
                print(f"{Fore.RED}[DEBUG CRITICAL] syspxy failure."); traceback.print_exc(); return

        active_df = pms.get_positions_df(client)
        any_order_placed, table_summary_data = False, []
        if not active_df.empty:
            sym_col = "symbol" if "symbol" in active_df.columns else "trading_symbol"
            qty_col = "qty" if "qty" in active_df.columns else ("netqty" if "netqty" in active_df.columns else "quantity")
            token_col = next((c for c in active_df.columns if c.lower() in ['instrument_token', 'token', 'token_id', 'tok', 'asset_token']), None)
            seg_col = next((c for c in active_df.columns if c.lower() in ['exchange_segment', 'segment', 'exchange', 'exseg']), None)
            avg_col = next((c for c in active_df.columns if c.lower() in ['avg_price', 'average_price', 'buy_price', 'netavgprc', 'buy_avg_price', 'prc']), None)

            for _, row in active_df.iterrows():
                try:
                    symbol, qty = str(row.get(sym_col, "")).upper().strip(), pms.safe_int_convert(row.get(qty_col), 0)
                    if not symbol or symbol in ['NAN', 'NONE', ''] or qty == 0: continue
                    avg_price = pms.safe_float_convert(row.get(avg_col), 0.0)
                    live_price = pms.fetch_live_mid_price(client, row, token_col, seg_col)
                    pnl_points = live_price - avg_price if live_price > 0.0 else 0.0
                    table_summary_data.append({"symbol": symbol, "qty": qty, "mid": live_price, "avg": avg_price, "pnl": pnl_points})

                    if ("CE" in symbol and exit_signal in ["BULL", "BUY"]) or ("PE" in symbol and exit_signal in ["BEAR", "SELL"]):
                        print(f"{Fore.CYAN}🛡️ MOMENTUM HOLD: Keeping {symbol} | Signal is {exit_signal}"); continue
                    if atr_val is None or avg_col is None or avg_price <= 0.0 or live_price <= 0.0:
                        print(f"{Fore.RED}[DEBUG ALERT] Metrics missing for {symbol}. Action: DO NOTHING."); continue
                    math_res = calculate_target_profit(qty, atr_val)
                    if math_res is None: print(f"{Fore.RED}[DEBUG ALERT] Math anomaly for {symbol}. Action: DO NOTHING."); continue
                    target_profit_points, count = math_res
                    if pnl_points < target_profit_points:
                        print(f"{Fore.YELLOW}⏳ TARGET NOT MET: Holding {symbol} | Gained: {pnl_points:.2f} / Target: {target_profit_points:.2f} (Count: {count:.2f})"); continue
                    else:
                        print(f"{Fore.GREEN}🎯 TARGET ACHIEVED: {symbol} reached {pnl_points:.2f} points (Target: {target_profit_points:.2f})")
                    if place_exit_order(client, row, sym_col, qty_col): any_order_placed = True
                except Exception:
                    print(f"{Fore.RED}[DEBUG CRITICAL] Row iteration failed:"); traceback.print_exc(); continue

        pms.print_portfolio_table(table_summary_data)
        if any_order_placed:
            try:
                script_path = os.path.join(str(HERE), "sysddmppxy.py")
                if os.path.exists(script_path): subprocess.Popen(["python3", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception: print(f"{Fore.RED}[DEBUG CRITICAL] Matrix script failed."); traceback.print_exc()
        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 Risk loop pass completed.")
    except Exception: print(f"{Fore.RED}[DEBUG CRITICAL] Master exception."); traceback.print_exc()

if __name__ == "__main__":
    main()
