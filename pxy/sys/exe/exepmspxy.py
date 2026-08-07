import sys
import os
import subprocess
import traceback
from pathlib import Path
import pandas as pd
import pytz
from datetime import datetime
from colorama import Fore, Style

# --- DYNAMIC SUBDIRECTORY PATH SCANNING FOR HELPER ---
HERE = Path(__file__).resolve().parent
run_dir = os.path.join(str(HERE), "run")
if run_dir not in sys.path:
    sys.path.append(run_dir)

from runltpspxy import get_mid_price

def safe_float_convert(val, default=None):
    if val is None or pd.isna(val): return default
    try: return float(str(val).replace(',', '').strip())
    except Exception: return default

def safe_int_convert(val, default=0):
    if val is None or pd.isna(val): return default
    try: return int(str(val).split('.')[0].replace(',', '').strip())
    except Exception: return default

def get_sell_suffix():
    IST = pytz.timezone("Asia/Kolkata")
    return f"_S{datetime.now(IST).strftime('%f')[:-3]}"

def fetch_live_mid_price(client, row, token_col, seg_col):
    live_val = 0.0
    raw_token = row.get(token_col) if token_col else None
    token_id = str(raw_token).split('.')[0].strip() if raw_token else None
    raw_seg = str(row.get(seg_col, "nse_fo")).strip()
    ex_seg = "nse_fo" if raw_seg.lower() in ["nse_fo", "nfo"] else raw_seg.lower()
    if not client or not token_id: return live_val
    try: live_val = float(get_mid_price(client, token_id, ex_seg))
    except Exception: pass
    if live_val <= 0:
        try:
            t_payload = [{"instrument_token": str(token_id), "exchange_segment": str(ex_seg)}]
            v2_q = client.quotes(instrument_tokens=t_payload, quote_type="ltp")
            chunk = v2_q.get("data") or v2_q.get("message") or v2_q if isinstance(v2_q, dict) else v2_q
            if isinstance(chunk, list) and len(chunk) > 0: live_val = float(chunk[0].get("ltp") or chunk[0].get("lastTradedPrice") or 0)
            elif isinstance(chunk, dict): live_val = float(chunk.get("ltp") or chunk.get("lastTradedPrice") or 0)
        except Exception: pass
    if live_val <= 0:
        try:
            scr_res = client.search_scrip(exchangeSegment=ex_seg, instrumentToken=str(token_id))
            if isinstance(scr_res, list) and len(scr_res) > 0: live_val = float(scr_res[0].get("ltp") or scr_res[0].get("lastPrice") or 0)
            elif isinstance(scr_res, dict): live_val = float(scr_res.get("ltp") or scr_res.get("lastPrice") or 0)
        except Exception: pass
    return live_val

def get_positions_df(client):
    try:
        res = client.positions()
        return pd.DataFrame(res["data"]) if res and "data" in res and res["data"] else pd.DataFrame()
    except Exception:
        print(f"{Fore.RED}[DEBUG CRITICAL] Broker API Positions Call Crashed. Full Traceback:")
        traceback.print_exc(); return pd.DataFrame()

def print_portfolio_table(summary_list):
    print(f"\n{Style.BRIGHT}{Fore.YELLOW}+-------------------------+--------+------------+------------+------------+")
    print(f"{Style.BRIGHT}{Fore.YELLOW}| SYMBOL                  | QTY    | MID PRICE  | AVG PRICE  | PNL POINTS |")
    print(f"{Style.BRIGHT}{Fore.YELLOW}+-------------------------+--------+------------+------------+------------+")
    if not summary_list:
        msg = "No active tracking rows inside portfolio matrix."
        print(f"| {Fore.LIGHTBLACK_EX}{msg:64}{Style.BRIGHT}{Fore.YELLOW} |")
    else:
        for item in summary_list:
            sym, qty, mid, avg, pnl = f"{item['symbol']:23}", f"{item['qty']:6}", f"{item['mid']:10.2f}", f"{item['avg']:10.2f}", item['pnl']
            pnl_str = f"{Fore.GREEN if pnl >= 0 else Fore.RED}{pnl:10.2f}{Style.RESET_ALL}{Style.BRIGHT}{Fore.YELLOW}"
            print(f"| {sym} | {qty} | {mid} | {avg} | {pnl_str} |")
    print(f"+-------------------------+--------+------------+------------+------------+\n")

