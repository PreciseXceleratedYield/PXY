# _exit.py
import sys
import asyncio
import os
import json
from datetime import datetime, time as dt_time
import pytz
import yfinance as yf
import pandas as pd
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42  # Shared 42-character width constraint engine

LOT_SIZE = 65     
MIN_EXIT_PROFIT = 200         

init(autoreset=True)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_historical_index_price_by_tag(df_history, tag_string):
    try:
        if not tag_string or len(str(tag_string)) < 4: return 0.0
        tag_str = str(tag_string).strip()
        hh = int(tag_str[:2])
        mm = int(tag_str[2:4])
        for idx_time, row in df_history.iterrows():
            if idx_time.hour == hh and idx_time.minute == mm:
                return float(row['Close'])
    except: pass
    return 0.0

def reconstruct_fifo_ledger_from_tags(client, df_history):
    ledger_reconstructed = []
    try:
        pos_res = client.positions()
        positions = pos_res.get("data", [])
        if not positions or not isinstance(positions, list): return []

        raw_nodes = []
        for pos in positions:
            net_qty = float(pos.get("net_qty", 0))
            if net_qty == 0: net_qty = float(pos.get("flBuyQty", 0)) - float(pos.get("flSellQty", 0))
            
            if abs(net_qty) > 0:
                sym = str(pos.get("trdSym", "")).upper()
                if sym.endswith("CE") and "NIFTY" in sym and "BANKNIFTY" not in sym:
                    tag = pos.get("tag", pos.get("orderTag", pos.get("text", "")))
                    entry_idx_price = get_historical_index_price_by_tag(df_history, tag)
                    if entry_idx_price == 0.0: 
                        entry_idx_price = float(pos.get("actPrc", pos.get("buyPrc", 0)))
                    
                    txn_type = "B" if net_qty > 0 else "S"
                    raw_nodes.append({
                        "symbol": sym, "txn_type": txn_type, "entry_ltp": entry_idx_price, 
                        "qty": int(abs(net_qty)), "tag": str(tag)
                    })

        raw_nodes.sort(key=lambda x: x['tag'])
        for node in raw_nodes:
            lots_count = int(node['qty'] / LOT_SIZE)
            for _ in range(lots_count):
                ledger_reconstructed.append({
                    "symbol": node['symbol'], "txn_type": node['txn_type'], 
                    "entry_ltp": node['entry_ltp'], "qty": LOT_SIZE
                })
    except Exception as e:
        err_msg = f"❌ Tag Error: {str(e)[:24]}"
        print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))
    return ledger_reconstructed

def execute_exit(client, symbol, qty, txn_type):
    try:
        order_tag = f"{datetime.now().strftime('%H%M%S')}_EX"
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": txn_type, "amo": "NO", "tag": order_tag  
        }
        res = client.place_order(**params)
        if res and str(res).strip():
            out_str = f"🏁 EXIT OK | {symbol[:15]} | {txn_type}"
            print(_pad_line_to_42(out_str, Fore.MAGENTA + Style.BRIGHT, Style.RESET_ALL))
            return True
    except Exception as e:
        err_msg = f"❌ Exit Error: {str(e)[:24]}"
        print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))
    return False

def force_global_account_flatten(client):
    try:
        pos_res = client.positions()
        positions = pos_res.get("data", [])
        if not positions or not isinstance(positions, list): return

        for pos in positions:
            net_qty = float(pos.get("net_qty", 0))
            if net_qty == 0: net_qty = float(pos.get("flBuyQty", 0)) - float(pos.get("flSellQty", 0))
            
            if abs(net_qty) > 0:
                sym = str(pos.get("trdSym", "")).upper()
                if sym.endswith("CE") and "NIFTY" in sym and "BANKNIFTY" not in sym:
                    exit_txn = "S" if net_qty > 0 else "B"
                    out_str = f"🚨 EOD AUTO-COLLAPSE: {sym[:17]}"
                    print(_pad_line_to_42(out_str, Fore.RED + Style.BRIGHT, Style.RESET_ALL))
                    execute_exit(client, sym, int(abs(net_qty)), exit_txn)
    except Exception as e:
        err_msg = f"❌ Critical EOD Fail: {str(e)[:20]}"
        print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))

def dump_to_json(current_live_list): 
    try: 
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "pnl.json")
        
        IST = pytz.timezone("Asia/Kolkata")
        existing_records = []

        if os.path.exists(file_path):
            mtime = os.path.getmtime(file_path)
            mtime_date = datetime.fromtimestamp(mtime, tz=pytz.utc).astimezone(IST).date()
            current_date = datetime.now(IST).date()
            
            if mtime_date < current_date:
                try:
                    os.remove(file_path)
                except:
                    pass
            else:
                try:
                    with open(file_path, "r") as f:
                        existing_records = json.load(f)
                        if not isinstance(existing_records, list):
                            existing_records = []
                except:
                    pass

        # Build lookup tables to match state changes safely across script executions
        historical_closed = [r for r in existing_records if r.get("Exit_Time") != "OPEN"]
        previously_open = [r for r in existing_records if r.get("Exit_Time") == "OPEN"]
        
        # Track symbol occurrences in the current active frame to align matching indices
        current_live_counts = {}
        processed_live_entries = []

        for item in current_live_list:
            sym = item["Symbol"]
            idx = current_live_counts.get(sym, 0)
            current_live_counts[sym] = idx + 1
            
            # Map index unique footprint key directly onto item properties
            item["_state_key"] = f"{sym}_{idx}"
            processed_live_entries.append(item)

        # Re-verify and isolate open positions from previous execution frames
        prev_open_counts = {}
        for item in previously_open:
            sym = item["Symbol"]
            idx = prev_open_counts.get(sym, 0)
            prev_open_counts[sym] = idx + 1
            
            state_key = f"{sym}_{idx}"
            
            # If an item was active before but missing now, lock it as inactive (CLOSED)
            if not any(live.get("_state_key") == state_key for live in processed_live_entries):
                item["Exit_Time"] = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                historical_closed.append(item)

        # Clean state fields before dumping data
        for live_item in processed_live_entries:
            if "_state_key" in live_item:
                del live_item["_state_key"]

        # Final export includes historically closed data mixed with latest tracked snapshots
        final_dataset = historical_closed + processed_live_entries
        
        # DataFrame conversion handles datetime type standardization dynamically
        df_temp = pd.DataFrame(final_dataset)
        if not df_temp.empty:
            for col in df_temp.columns:
                if pd.api.types.is_datetime64_any_dtype(df_temp[col]):
                    df_temp[col] = df_temp[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            data_to_dump = df_temp.to_dict(orient='records')
        else:
            data_to_dump = []

        with open(file_path, "w") as f: 
            json.dump(data_to_dump, f, indent=4) 
    except Exception as e: 
        print(f"Error dumping to JSON: {e}") 

async def exit_cycle():
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()

    from _sgnl import get_all_data, apply_mode_5_transformation, TIMEZONE
    from _clnt import get_session

    client = get_session()
    if not client: return

    if dt_time(15, 20) <= now < dt_time(15, 26):
        clear_screen()
        print(_pad_line_to_42("⏳ EOD LIMIT: 3:20 PM IST FORCED FLATTEN", Fore.RED + Style.BRIGHT, Style.RESET_ALL))
        force_global_account_flatten(client)
        return

    if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 25) <= now < dt_time(15, 31)): 
        clear_screen()
        print(_pad_line_to_42("⏳ SYSTEM IDLE: BUFFER TIMING BLOCK", Fore.YELLOW, Style.RESET_ALL))
        return

    data = get_all_data()
    entry_signal = str(data.get("entry", "")).upper().strip()
    ltp = float(data.get("price", 0))
    if ltp == 0 or not entry_signal: return

    ticker_obj = yf.Ticker("^NSEI")
    df_raw = ticker_obj.history(period="1d", interval="1m")
    if df_raw.empty: return
    df_raw.dropna(inplace=True)
    df_raw.index = pd.to_datetime(df_raw.index).tz_convert(TIMEZONE)
    df_history = apply_mode_5_transformation(df_raw)

    ledger = reconstruct_fifo_ledger_from_tags(client, df_history)

    clear_screen()
    border = "==========================================" # 42 chars
    print(_pad_line_to_42("📋 STATELESS FIFO MONITOR DASHBOARD", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42(border, Fore.YELLOW, Style.RESET_ALL))
    print(_pad_line_to_42(f"🎯 INDEX LTP : {ltp:<23}", Fore.CYAN, Style.RESET_ALL))
    print(_pad_line_to_42(f"🚦 SIGNAL    : {entry_signal:<23}", Fore.MAGENTA, Style.RESET_ALL))
    print(_pad_line_to_42(border, Fore.YELLOW, Style.RESET_ALL))

    if not ledger:
        print(_pad_line_to_42("⚪ NO ACTIVE TRACKED POSITIONS FOUND", Fore.WHITE + Style.DIM, Style.RESET_ALL))
        print(_pad_line_to_42(border, Fore.YELLOW, Style.RESET_ALL))
        dump_to_json([])
        return

    exit_executed = False
    current_live_snapshot = []




