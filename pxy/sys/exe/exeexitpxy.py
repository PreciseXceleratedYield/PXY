# exit_script.py 
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

init(autoreset=True) 

DEBUG_MODE = True 

def debug_log(msg, color=Fore.BLUE): 
    if DEBUG_MODE: 
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}") 

def get_sell_suffix():
    """Generates an explicit sell suffix code with millisecond resolution"""
    IST = pytz.timezone("Asia/Kolkata")
    ms = datetime.now(IST).strftime('%f')[:-3]
    return f"_S{ms}" # Returns pattern like _S412

def place_exit_order(client, row): 
    """Triggers Sell order by appending an explicit _S{ms} suffix to the entry tag.""" 
    try: 
        existing_tag = row.get('tag') 
        
        # Clean and extract the original entry tag baseline
        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']: 
            # Strip away any existing suffix tokens if present
            base_tag = str(existing_tag).split('_')[0].strip()
        else: 
            IST = pytz.timezone("Asia/Kolkata")
            base_tag = datetime.now(IST).strftime('%H%M%S')
            
        # FIX: Structure final tag with explicit sell suffix code
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
            try:
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                script_path = os.path.join(parent_dir, "sysddmppxy.py")
                if os.path.exists(script_path):
                    subprocess.Popen(["python3", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    print(f"{Fore.RED}❌ Script not found at {script_path}")
            except Exception as script_err:
                print(f"{Fore.RED}❌ Error launching script: {script_err}")
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
    try: 
        ltp = float(row.get("sell_prc", 0)) 
        tgt = float(row.get("pxy_tgt", 0)) 
        entry = float(row.get("pxy_entry", 0)) 
        if ltp <= 0 or entry <= 0: 
            return "%00⚪ 00%", False 
        entry_pct = int(((ltp - entry) / entry) * 100) 
        tgt_pct = int(((tgt - ltp) / entry) * 100) 
        entry_pct = max(-99, min(99, entry_pct)) 
        tgt_pct = max(0, min(99, tgt_pct)) 
        color, dot = (Fore.GREEN, "🟢") if entry_pct > 0 else (Fore.RED, "🔴") if entry_pct < 0 else (Fore.WHITE, "⚪") 
        st_str = f"{color}%{abs(entry_pct):02d}{dot}{Fore.RESET} {tgt_pct:02d}%" 
        return st_str, (ltp >= tgt) 
    except: 
        return "%00⚪ 00%", False 

def run_snapshot(): 
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
        
        # Colorize CE word green and PE word red inside the symbol string
        if "CE" in sym:
            sym_display = sym.replace("CE", f"{Fore.GREEN}CE{Fore.RESET}")
        elif "PE" in sym:
            sym_display = sym.replace("PE", f"{Fore.RED}PE{Fore.RESET}")
        else:
            sym_display = sym

        st_display, is_target_hit = compute_st_fixed(r) 
        if is_target_hit: 
            verify_and_exit(client, r) 
        pnl_val = int(r.get('pnl', 0)) 
        p_col = Fore.GREEN if pnl_val > 0 else Fore.RED if pnl_val < 0 else Fore.WHITE 
        
        # Swapped {sym:<20} for {sym_display:<20} to implement the color format change
        print(f" {sym_display:<20}{st_display:<12}{p_col}{pnl_val:>8}") 
    print("-" * 42) 
    print(f"{Fore.WHITE}Refreshed: {datetime.now(IST).strftime('%H:%M:%S')}") 

if __name__ == "__main__": 
    run_snapshot()

