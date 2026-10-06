# exesqrpxy.py
import sys 
import os 
import subprocess
from pathlib import Path

# Add the system and run directories before importing local modules.
current_dir = os.path.dirname(os.path.abspath(__file__)) 
run_dir = os.path.join(current_dir, "run") 
sys_dir = str(Path(__file__).resolve().parent.parent)
if sys_dir not in sys.path:
    sys.path.insert(0, sys_dir)
sys.path.append(run_dir) 

from runclntpxy import get_session 
import pandas as pd 
from exeomspxy import get_combined_data 
from colorama import Fore, Style, init 
from datetime import datetime
from syscnfgpxy import (
    EXEEXITPXY_ORDER_AMO,
    EXEEXITPXY_ORDER_EXCHANGE_SEGMENT,
    EXEEXITPXY_ORDER_PRICE,
    EXEEXITPXY_ORDER_PRODUCT,
    EXEEXITPXY_ORDER_TRANSACTION_TYPE,
    EXEEXITPXY_ORDER_TYPE,
    EXEEXITPXY_ORDER_VALIDITY,
    EXESQRPXY_EXIT_ALL_AFTER,
    SYSCNFGPXY_TIMEZONE,
)

init(autoreset=True) 

def get_sell_suffix():
    """Generates an explicit sell suffix code with millisecond resolution to ensure unique IDs"""
    ms = datetime.now(SYSCNFGPXY_TIMEZONE).strftime('%f')[:-3]
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
            base_tag = datetime.now(SYSCNFGPXY_TIMEZONE).strftime('%H%M%S')
            
        # FIX: Structure final tag with explicit sell suffix code matching your LILO engine
        final_tag = f"{base_tag}{get_sell_suffix()}"
            
        params = { 
            "exchange_segment": EXEEXITPXY_ORDER_EXCHANGE_SEGMENT,
            "product": EXEEXITPXY_ORDER_PRODUCT,
            "price": EXEEXITPXY_ORDER_PRICE,
            "order_type": EXEEXITPXY_ORDER_TYPE,
            "quantity": str(abs(int(qty))), 
            "validity": EXEEXITPXY_ORDER_VALIDITY,
            "trading_symbol": str(symbol), 
            "transaction_type": EXEEXITPXY_ORDER_TRANSACTION_TYPE,
            "amo": EXEEXITPXY_ORDER_AMO,
            "tag": final_tag 
        } 
        
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXITING POSITION: {symbol} Qty: {qty} | TAG: {final_tag}") 
        
        # FIX: Defined order_response properly first
        order_response = client.place_order(**params) 
        
        # FIX FOR VM FREEZE: Background launcher process loop removed from here entirely!
        return order_response

    except Exception as e: 
        print(f"{Fore.RED}❌ Exit Order Error for {row.get('symbol')}: {e}") 
        return None 

def exit_all_positions(): 
    now = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    client = get_session() 
    if not client: 
        print(f"{Fore.RED}❌ Session not initialized. Exiting...") 
        return 
        
    data = get_combined_data() 
    if data.get("error"):
        print(f"{Fore.RED}⚠️ OMS data unavailable; square-off skipped to avoid treating an API failure as flat.")
        return
    active_df = data.get("active_orders", pd.DataFrame()) 
    market_df = data.get("market_snapshot", pd.DataFrame()) 
    
    # --- DYNAMIC CLI FILTER BYPASS & PANIC SWITCH ---
    force_all_bypass = False
    if len(sys.argv) > 1 and not active_df.empty:
        target_param = sys.argv[1].lower().strip()
        if target_param == "-all":
            print(f"{Fore.RED}{Style.BRIGHT}🚨 PANIC BYPASS: Nilling out ALL active positions immediately!")
            force_all_bypass = True
        elif target_param == "-ce":
            print(f"{Fore.YELLOW}⚠️ CLI BYPASS: Filtering ONLY CE positions for immediate square-off.")
            active_df = active_df[active_df["symbol"].str.contains("CE", na=False)]
        elif target_param == "-pe":
            print(f"{Fore.YELLOW}⚠️ CLI BYPASS: Filtering ONLY PE positions for immediate square-off.")
            active_df = active_df[active_df["symbol"].str.contains("PE", na=False)]
            
    if active_df.empty: 
        print(f"{Fore.YELLOW}No active positions to exit.{Fore.RESET}") 
        return 
        
    direction = market_df["direction"].iloc[-1] if not market_df.empty and "direction" in market_df.columns else None 
    exit_all_after = EXESQRPXY_EXIT_ALL_AFTER
    
    # FIX FOR VM FREEZE: Track if any single trade actually fires an order response
    any_order_placed = False
    
    for _, row in active_df.iterrows(): 
        symbol = row.get("symbol") 
        qty = row.get("qty", 0) 
        if not symbol or qty == 0: 
            continue 
            
        # If the manual panic flag is active or it is past 3:25 PM, flatten immediately
        if force_all_bypass or now >= exit_all_after: 
            if place_exit_order(client, row):
                any_order_placed = True
        else: 
            # Normal rule-based trend management
            if direction == "UP" and "PE" in symbol: 
                if place_exit_order(client, row):
                    any_order_placed = True
            elif direction == "DOWN" and "CE" in symbol: 
                if place_exit_order(client, row):
                    any_order_placed = True
            else: 
                print(f"{Fore.CYAN}Holding {symbol} | Direction: {direction}") 
                
    # --- FIX FOR VM FREEZE: SURGICAL BACKGROUND LAUNCHER OUTSIDE THE LOOP ---
    # Fires EXACTLY ONCE to update your data matrices safely without crashing the storage
    if any_order_placed:
        try:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(parent_dir, "sysddmppxy.py")
            if os.path.exists(script_path):
                subprocess.Popen(["python3", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print(f"{Fore.RED}❌ Script not found at {script_path}")
        except Exception as script_err:
            print(f"{Fore.RED}❌ Error launching script: {script_err}")
            
    print(f"{Fore.GREEN}{Style.BRIGHT}✅ Exit attempt completed.") 

if __name__ == "__main__": 
    exit_all_positions()
