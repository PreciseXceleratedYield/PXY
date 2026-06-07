# exesqrpxy.py
import sys 
import os 

# Add the 'run' subfolder of the current script to Python path 
current_dir = os.path.dirname(os.path.abspath(__file__)) 
run_dir = os.path.join(current_dir, "run") 
sys.path.append(run_dir) 

from runclntpxy import get_session 
import pandas as pd 
from exeomspxy import get_combined_data 
from colorama import Fore, Style, init 
import pytz 
from datetime import datetime, time as dt_time 

init(autoreset=True) 

def get_sell_suffix():
    """Generates an explicit sell suffix code with millisecond resolution to ensure unique IDs"""
    IST = pytz.timezone("Asia/Kolkata")
    ms = datetime.now(IST).strftime('%f')[:-3]
    return f"_S{ms}"

def place_exit_order(client, row): 
    """Triggers Sell order by appending an explicit _S{ms} suffix to the entry tag."""
    try: 
        symbol = row.get("symbol")
        qty = row.get("qty", 0)
        existing_tag = row.get('tag') 
        
        # Clean and extract the original entry tag baseline
        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']: 
            # Strip away any old suffix tokens if present
            base_tag = str(existing_tag).split('_')[0].strip()
        else: 
            IST = pytz.timezone("Asia/Kolkata")
            base_tag = datetime.now(IST).strftime('%H%M%S')
            
        # FIX: Structure final tag with explicit sell suffix code matching your LILO engine
        final_tag = f"{base_tag}{get_sell_suffix()}"
            
        params = { 
            "exchange_segment": "nse_fo", 
            "product": "NRML", 
            "price": "0", 
            "order_type": "MKT", 
            "quantity": str(abs(int(qty))), 
            "validity": "DAY", 
            "trading_symbol": str(symbol), 
            "transaction_type": "S", 
            "amo": "NO", 
            "tag": final_tag 
        } 
        
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXITING POSITION: {symbol} Qty: {qty} | TAG: {final_tag}") 
        return client.place_order(**params) 
    except Exception as e: 
        print(f"{Fore.RED}❌ Exit Order Error for {row.get('symbol')}: {e}") 
        return None 

def exit_all_positions(): 
    IST = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(IST).time() 
    client = get_session() 
    if not client: 
        print(f"{Fore.RED}❌ Session not initialized. Exiting...") 
        return 
        
    data = get_combined_data() 
    active_df = data.get("active_orders", pd.DataFrame()) 
    market_df = data.get("market_snapshot", pd.DataFrame()) 
    
    # --- DYNAMIC CLI FILTER BYPASS ---
    if len(sys.argv) > 1 and not active_df.empty:
        target_param = sys.argv[1].lower().strip()
        if target_param == "-ce":
            print(f"{Fore.YELLOW}⚠️ CLI BYPASS: Filtering ONLY CE positions for immediate square-off.")
            active_df = active_df[active_df["symbol"].str.contains("CE", na=False)]
        elif target_param == "-pe":
            print(f"{Fore.YELLOW}⚠️ CLI BYPASS: Filtering ONLY PE positions for immediate square-off.")
            active_df = active_df[active_df["symbol"].str.contains("PE", na=False)]
            
    if active_df.empty: 
        print(f"{Fore.YELLOW}No active positions to exit.{Fore.RESET}") 
        return 
        
    direction = market_df["direction"].iloc[-1] if not market_df.empty and "direction" in market_df.columns else None 
    exit_all_after = dt_time(15, 25) # 3:25 PM 
    
    for _, row in active_df.iterrows(): 
        symbol = row.get("symbol") 
        qty = row.get("qty", 0) 
        if not symbol or qty == 0: 
            continue 
            
        if now < exit_all_after: 
            if direction == "UP" and "PE" in symbol: 
                # FIX: Passed the entire row object to handle tag extraction
                place_exit_order(client, row) 
            elif direction == "DOWN" and "CE" in symbol: 
                place_exit_order(client, row) 
            else: 
                print(f"{Fore.CYAN}Holding {symbol} | Direction: {direction}") 
        else: 
            place_exit_order(client, row) 
            
    print(f"{Fore.GREEN}{Style.BRIGHT}✅ Exit attempt completed.") 

if __name__ == "__main__": 
    exit_all_positions()

