# # exeenexpxy.py
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

# 🎯 UPDATED FILE IMPORT NAME: Pointing directly to exerskmgtpxy.py
try:
    from exerskmgtpxy import check_trend_collapse_exit
except ImportError:
    check_trend_collapse_exit = lambda df, client: False

init(autoreset=True) 

DEBUG_MODE = False 

# ==========================================================
# CONFIGURATION SWITCH (LOCKED IN CONTROLLER)
# Options: 
#   "one" -> ALWAYS exits individual positions as they hit targets.
#   "all" -> Dynamic Hybrid Matrix (evaluates balance / protects sides).
# ==========================================================
EXIT_MODE = "one" 

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
        dump_idle_json(EXIT_MODE)
        return 
        
    # 🎯 SURGICAL ADDITION: Intercept system state before averaging fires
    if check_trend_collapse_exit(df, client): return
        
    handle_side_averaging(client, df) 

if __name__ == "__main__": 
    run_snapshot()
