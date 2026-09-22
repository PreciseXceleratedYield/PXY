# # exeexitpxy.py
import pandas as pd 
import os 
import time 
import pytz 
import subprocess 
from datetime import datetime, time as dt_time 
from colorama import init, Fore, Style 

from exeomspxy import get_combined_data 
from runclntpxy import get_session 

# IMPORT SYSTEM CO-PROCESSOR 
from exeexppxy import analyze_targets_and_sides, process_metrics_print_and_dump, dump_idle_json

# 🎯 UPDATED FILE IMPORT NAME: Pointing directly to exerskmgtpxy.py
try:
    from exerskmgtpxy import check_trend_collapse_exit
except ImportError:
    check_trend_collapse_exit = lambda df, client: False

init(autoreset=True) 

DEBUG_MODE = False 

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
    
    # Base path to the script
    exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exesqrpxy.py")
    
    if os.path.exists(exe_path):
        try:
            # 1. Runs from 15:11 up to 15:14:59 (Without "-all")
            if dt_time(15, 14) <= now < dt_time(15, 15):
                subprocess.run(["python3", exe_path], check=True)
                
            # 2. Runs from 15:15 up to 15:49:59 (With "-all")
            elif dt_time(15, 15) <= now < dt_time(15, 50):
                subprocess.run(["python3", exe_path, "-all"], check=True)
                
        except Exception as e:
            print(f"{Fore.RED}❌ Square-off Error: {e}")

    data = get_combined_data() 
    df = data.get("active_orders", pd.DataFrame()) 
    client = get_session() 
    if df.empty: 
        print(f"{Fore.YELLOW}No active orders. System idling...") 
        dump_idle_json("one")
        return 
        
    # 🎯 SURGICAL ADDITION: Intercept system state before target analysis fires
    if check_trend_collapse_exit(df, client): return
        
    side_all_targets_hit = analyze_targets_and_sides(df)

    # Proactive Core Execution Routing Logic Block (Pure Single Targets)
    for idx, r in df.iterrows():
        sym = str(r.get('symbol', ''))
        ltp = float(r.get("sell_prc", 0))
        tgt = float(r.get("pxy_tgt", 0))
        pnl = float(r.get("pnl", 0))

        debug_log(f"Global Enforced Single Exit Mode ({sym}). Mode: SINGLE TARGET.", Fore.GREEN)

        # Pure Linear Target Evaluation Pool
        if ltp >= tgt and pnl >= 140:
            print(f"{Fore.GREEN}🎯 Target Hit & PnL Met ({sym}): LTP {ltp} >= TGT {tgt} | PnL {pnl} >= 140 [Execution Mode: ONE]")
            verify_and_exit(client, r)

    process_metrics_print_and_dump(df, side_all_targets_hit, "one")

if __name__ == "__main__": 
    run_snapshot()
