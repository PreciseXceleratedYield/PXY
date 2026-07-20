# exeexitpxy.py
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

# IMPORT SYSTEM CO-PROCESSOR 
from exeexppxy import analyze_targets_and_sides, process_metrics_print_and_dump, dump_idle_json

init(autoreset=True) 

DEBUG_MODE = False 

# ==========================================================
# CONFIGURATION SWITCH (LOCKED IN CONTROLLER)
# Options: 
#   "one" -> Exits individual positions as they hit targets.
#   "all" -> Exits a side only when ALL positions on that side hit targets.
# ==========================================================
EXIT_MODE = "one" 

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
        dump_idle_json(EXIT_MODE)
        return 

    handle_side_averaging(client, df) 
    
    side_all_targets_hit = analyze_targets_and_sides(df)

    # DYNAMIC COUNT ASSESSMENT: Extract exact row integer using index 0
    ce_count = df[df['symbol'].str.contains('CE', na=False, case=True)].shape[0]
    pe_count = df[df['symbol'].str.contains('PE', na=False, case=True)].shape[0]

    debug_log(f"Active Hedge Matrix Structure -> CE Split Rows: {ce_count} | PE Split Rows: {pe_count}", Fore.CYAN)

    # Proactive Core Execution Routing Logic Block
    for idx, r in df.iterrows():
        sym = str(r.get('symbol', ''))
        ltp = float(r.get("sell_prc", 0))
        tgt = float(r.get("pxy_tgt", 0))

        # Condition 1: Solo Side Active
        if ce_count == 0 or pe_count == 0:
            effective_mode = "one"
            debug_log(f"Solo Side Active ({sym}). Mode: SINGLE TARGET.", Fore.YELLOW)

        # Condition 2: Perfectly Equal Row Count Symmetry -> Enforce "All-or-Nothing"
        elif ce_count == pe_count:
            effective_mode = EXIT_MODE  
            debug_log(f"Hedge Matrix Equalized ({ce_count} == {pe_count} rows). Mode: ALL-OR-NOTHING.", Fore.BLUE)

        # Condition 3: Imbalanced Structural Rows
        else:
            if "CE" in sym and ce_count > pe_count:
                effective_mode = "one"
                debug_log(f"Heavy Side: CE ({ce_count} > {pe_count} rows). Mode: SINGLE TARGET.", Fore.MAGENTA)
            elif "PE" in sym and pe_count > ce_count:
                effective_mode = "one"
                debug_log(f"Heavy Side: PE ({pe_count} > {ce_count} rows). Mode: SINGLE TARGET.", Fore.MAGENTA)
            else:
                effective_mode = "all"
                debug_log(f"Lighter Side Protected Matrix Lot ({sym}). Mode: ALL-OR-NOTHING.", Fore.BLUE)

        # Route Order Processing Operations
        if effective_mode == "all":
            if ("CE" in sym and side_all_targets_hit.get("CE", False)) or ("PE" in sym and side_all_targets_hit.get("PE", False)):
                verify_and_exit(client, r)
        else:
            if ltp >= tgt:
                print(f"{Fore.GREEN}🎯 Dynamic Single Target Hit ({sym}): LTP {ltp} >= TGT {tgt} (Imbalanced Side Execution)")
                verify_and_exit(client, r)

    process_metrics_print_and_dump(df, side_all_targets_hit, EXIT_MODE)

if __name__ == "__main__": 
    run_snapshot()

