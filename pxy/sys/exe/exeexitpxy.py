# exit_script.py 
import pandas as pd 
import os 
import time 
import pytz 
import subprocess 
from datetime import datetime, time as dt_time 
from colorama import init, Fore, Style 

# External Dependency Imports 
from exeomspxy import get_combined_data 
from runclntpxy import get_session 
from exeavgpxy import handle_side_averaging 

init(autoreset=True) 

# --- DEBUG CONFIG --- 
DEBUG_MODE = True # FULL DEBUGGING ACTIVATED

def debug_log(msg, color=Fore.BLUE): 
    if DEBUG_MODE: 
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}") 

def generate_pxy_tag(): 
    """Generates a pure timestamp tag: HHMMSS""" 
    IST = pytz.timezone("Asia/Kolkata") 
    return datetime.now(IST).strftime('%H%M%S') 

def place_exit_order(client, row): 
    """Internal function to trigger the Sell order with the matching Tag.""" 
    try: 
        existing_tag = row.get('tag') 
        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']: 
            final_tag = str(existing_tag).strip() 
        else: 
            final_tag = generate_pxy_tag() 
            
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
        
        debug_log(f"Attempting API order placement payload: {params}", Fore.YELLOW)
        
        # Execute the order placement
        order_response = client.place_order(**params) 
        
        debug_log(f"Broker Raw API Response received: {order_response}", Fore.GREEN)
        
        if order_response: 
            print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ ORDER PLACED SUCCESSFULLY: {params['trading_symbol']} | TAG: {final_tag}") 
        return order_response 
        
    except Exception as e: 
        print(f"{Fore.RED}❌ Exit Order Error inside execution engine: {e}") 
        return None 

def verify_and_exit(client, row): 
    """SAFETY CHECK: Verifies with Broker (Kotak Neo) before selling.""" 
    try: 
        symbol = str(row.get('symbol', '')) 
        debug_log(f"Verifying open positions for symbol: {symbol}", Fore.CYAN)
        
        pos_res = client.positions() 
        debug_log(f"Raw Broker Positions Response Type: {type(pos_res)}", Fore.BLUE)
        
        if not pos_res or "data" not in pos_res: 
            print(f"{Fore.RED}⚠️ Safety Block: Could not verify positions with broker. 'data' key missing or empty.") 
            if DEBUG_MODE:
                print(f"{Fore.RED}[DEBUG] Full invalid response: {pos_res}")
            return 
            
        pos_df = pd.DataFrame(pos_res["data"]) 
        if DEBUG_MODE and not pos_df.empty:
            debug_log(f"Available tokens in positions: {pos_df['trdSym'].tolist()}", Fore.BLUE)
        
        match = pos_df[pos_df['trdSym'] == symbol] 
        if not match.empty: 
            net_qty = int(match['flBuyQty'].sum()) - int(match['flSellQty'].sum()) 
            debug_log(f"Symbol found! flBuyQty Sum: {match['flBuyQty'].sum()} | flSellQty Sum: {match['flSellQty'].sum()} | Net Calculated Qty: {net_qty}", Fore.CYAN)
            
            if net_qty > 0: 
                return place_exit_order(client, row) 
            else: 
                print(f"{Fore.YELLOW}🚫 Blocked: No active long position for {symbol} (Net Qty calculated: {net_qty})") 
        else: 
            print(f"{Fore.YELLOW}🚫 Blocked: Target symbol [{symbol}] not found anywhere in broker active positions matrix.") 
    except Exception as e: 
        print(f"{Fore.RED}❌ Critical Safety Verification Check Crash: {e}") 

def compute_st_fixed(row): 
    """Calculates status string and target hit boolean.""" 
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
        
        is_hit = (ltp >= tgt)
        if is_hit:
            debug_log(f"Target logic evaluated to TRUE for row. LTP: {ltp} >= TGT: {tgt}", Fore.MAGENTA)
            
        return st_str, is_hit 
    except Exception as e: 
        if DEBUG_MODE:
            print(f"{Fore.RED}[DEBUG] compute_st_fixed evaluation crash: {e}")
        return "%00⚪ 00%", False 

def run_snapshot(): 
    IST = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(IST).time() 
    
    if dt_time(15, 23) <= now < dt_time(15, 30): 
        try: 
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exesqrpxy.py") 
            if os.path.exists(exe_path): 
                debug_log("Inside Auto Square-Off time window. Initializing exesqrpxy.py sub-process.", Fore.YELLOW)
                subprocess.run(["python3", exe_path], check=True) 
        except Exception as e: 
            print(f"{Fore.RED}❌ Square-off Error: {e}") 

    debug_log("Fetching active OMS tracking database frames...", Fore.BLUE)
    data = get_combined_data() 
    df = data.get("active_orders", pd.DataFrame()) 
    client = get_session() 
    
    if df.empty: 
        print(f"{Fore.YELLOW}No active orders found in OMS cache frame. System idling...") 
        return 

    debug_log(f"OMS contains {len(df)} tracks. Sending rows to side averaging processor...", Fore.BLUE)
    handle_side_averaging(client, df) 

    print("━" * 42) 
    print(f" {Fore.CYAN}{Style.BRIGHT}{'SYMBOL':<21}{'ST':^10}{'PNL':>8}") 
    print("-" * 42) 
    
    for idx, r in df.iterrows(): 
        sym = str(r.get('symbol',''))[:21] 
        st_display, is_target_hit = compute_st_fixed(r) 
        
        if is_target_hit: 
            verify_and_exit(client, r) 
            
        pnl_val = int(r.get('pnl', 0)) 
        p_col = Fore.GREEN if pnl_val > 0 else Fore.RED if pnl_val < 0 else Fore.WHITE 
        print(f" {sym:<21}{st_display:<12}{p_col}{pnl_val:>8}") 
        
    print("-" * 42) 
    print(f"{Fore.WHITE}Refreshed: {datetime.now(IST).strftime('%H:%M:%S')}") 

if __name__ == "__main__": 
    run_snapshot()


