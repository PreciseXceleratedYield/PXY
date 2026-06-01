import pandas as pd 
import os 
import time 
import pytz 
import subprocess 
from datetime import datetime, time as dt_time 
from colorama import init, Fore, Style 

from exeomspxy import get_combined_data 
from runclntpxy import get_session 
from exeavgpxy import handle_side_averaging 

# FIX: Dynamic import link referencing your standalone math logic module
from exetgtpxy import target_price, PRINTED_SIDES

init(autoreset=True) 

DEBUG_MODE = True 

def debug_log(msg, color=Fore.BLUE): 
    if DEBUG_MODE: 
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}") 

def get_sell_suffix():
    """Generates an explicit sell suffix code with millisecond resolution"""
    IST = pytz.timezone("Asia/Kolkata")
    ms = datetime.now(IST).strftime('%f')[:-3]
    return f"_S{ms}" 

def place_exit_order(client, row): 
    """Triggers Sell order by appending an explicit _S{ms} suffix to the entry tag.""" 
    try: 
        existing_tag = row.get('tag') 
        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']: 
            base_tag = str(existing_tag).split('_')[0].strip()
        else: 
            IST = pytz.timezone("Asia/Kolkata")
            base_tag = datetime.now(IST).strftime('%H%M%S')
            
        final_tag = f"{base_tag}{get_sell_suffix()}"
            
        params = { 
            "exchange_segment": "nse_fo", 
            "product": "NRML", 
            "price": "0", 
            "order_type": "MKT", 
            "quantity": str(abs(int(row.get('qty', 0)))), 
            "validity": "DAY", 
            "trading_symbol": str(row.get('symbol', '')), 
            "transaction_type": "S", 
            "amo": "NO", 
            "tag": final_tag 
        } 
        
        debug_log(f"Attempting API exit payload: {params}", Fore.YELLOW) 
        order_response = client.place_order(**params) 
        debug_log(f"Broker Raw API Response: {order_response}", Fore.GREEN) 
        
        if isinstance(order_response, dict):
            stat_str = str(order_response.get('stat', '')).lower()
            err_msg = str(order_response.get('errMsg', '')).lower()
            if "failed" in stat_str or "error" in err_msg or "error" in stat_str:
                print(f"{Fore.RED}❌ BROKER CORE REJECTED ORDER: {err_msg} | {stat_str}")
                return None
        
        if order_response: 
            print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ ORDER PLACED ON EXCHANGE: {params['trading_symbol']} | TAG: {final_tag}") 
        return order_response 
        
    except Exception as e: 
        print(f"{Fore.RED}❌ Exit Order Error: {e}") 
        return None 

def verify_and_exit(client, row): 
    try: 
        symbol = str(row.get('symbol', '')) 
        pos_res = client.positions() 
        if not pos_res or "data" not in pos_res: 
            print(f"{Fore.RED}⚠️ Safety Block: Could not verify positions.") 
            return 
            
        pos_df = pd.DataFrame(pos_res["data"]) 
        if pos_df.empty or 'trdSym' not in pos_df.columns:
            return

        match = pos_df[pos_df['trdSym'] == symbol] 
        if not match.empty: 
            net_qty = int(match['flBuyQty'].sum()) - int(match['flSellQty'].sum()) 
            if net_qty > 0: 
                return place_exit_order(client, row) 
            else: 
                print(f"{Fore.YELLOW}🚫 Blocked: Net Qty calculated: {net_qty}") 
        else: 
            print(f"{Fore.YELLOW}🚫 Blocked: [{symbol}] not found in broker positions.") 
    except Exception as e: 
        print(f"{Fore.RED}❌ Safety Check Crash: {e}") 

def compute_st_fixed(row): 
    """
    Computes dashboard display metrics with normalized keys and automated math module links.
    """
    try: 
        # Normalize naming variations for incoming data keys from broker feeds
        ltp = float(row.get("sell_prc") or row.get("ltp") or 0) 
        entry = float(row.get("pxy_entry") or row.get("buy_prc") or row.get("entry_prc") or 0) 
        
        tgt = float(row.get("pxy_tgt") or 0)
        if tgt <= 0:
            # FIX: Unpack the target price integer safely from the calculation module's returned tuple
            tgt, _ = target_price(row)
            tgt = float(tgt)

        # Catch data validation drop errors cleanly
        if ltp <= 0 or entry <= 0 or tgt <= 0: 
            return f"{Fore.YELLOW}%--⚪ --%{Fore.RESET}", False 

        # Calculate tracking percentage deviations
        entry_pct = int(((ltp - entry) / entry) * 100) 
        tgt_pct = int(((tgt - ltp) / entry) * 100) 
        
        entry_pct = max(-99, min(99, entry_pct)) 
        tgt_pct = max(0, min(99, tgt_pct)) 
        
        color, dot = (Fore.GREEN, "🟢") if entry_pct > 0 else (Fore.RED, "🔴") if entry_pct < 0 else (Fore.WHITE, "⚪") 
        st_str = f"{color}%{abs(entry_pct):02d}{dot}{Fore.RESET} {tgt_pct:02d}%" 
        
        return st_str, (ltp >= tgt) 
    except Exception: 
        return f"{Fore.RED}%ERR⚪ ER%{Fore.RESET}", False 

def run_snapshot(): 
    # Clear the shared engine's side logging cache on each update loop
    PRINTED_SIDES.clear()
    
    IST = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(IST).time() 
    if dt_time(15, 23) <= now < dt_time(15, 30): 
        try: 
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exesqrpxy.py") 
            if os.path.exists(exe_path): 
                subprocess.run(["python3", exe_path], check=True) 
        except Exception as e: 
            print(f"{Fore.RED}❌ Square-off Error: {e}") 

    data = get_combined_data() 
    df = data.get("active_orders", pd.DataFrame()) 
    client = get_session() 
    if df.empty: 
        print(f"{Fore.YELLOW}No active orders. System idling...") 
        return 

    handle_side_averaging(client, df) 
    print("━" * 42) 
    print(f" {Fore.CYAN}{Style.BRIGHT}{'SYMBOL':<20}{'ST':^8}{'PL':>8}") 
    print("-" * 42) 
    for idx, r in df.iterrows(): 
        sym = str(r.get('symbol',''))[:21] 
        st_display, is_target_hit = compute_st_fixed(r) 
        if is_target_hit: 
            verify_and_exit(client, r) 
        pnl_val = int(r.get('pnl', 0)) 
        p_col = Fore.GREEN if pnl_val > 0 else Fore.RED if pnl_val < 0 else Fore.WHITE 
        print(f" {sym:<20}{st_display:<12}{p_col}{pnl_val:>8}") 
    print("-" * 42) 
    print(f"{Fore.WHITE}Refreshed: {datetime.now(IST).strftime('%H:%M:%S')}") 

if __name__ == "__main__": 
    run_snapshot()


