# sysavgpxy.py
"""
===============================================================================
PXY POSITION AVERAGING MANAGER: EXCLUSIVE LAYER ENGINE (OTM STRIKES ONLY)
===============================================================================
Operational Rules:
- Processes position averaging strictly for OTMBUY and OTMSELL cascades.
- Rebuys trigger up to MAX_LAYERS if ALL current layers breach FIXED_THRESHOLD_PCT.
- Cooldown timer locks rapid-fire loops out for COOL_DOWN_SECONDS.
===============================================================================
"""

import os 
import time 
import pytz 
import math
import sys
import subprocess
from pathlib import Path
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 2
COOL_DOWN_SECONDS = 60        # ⏱️ Cooling interval set to exactly 60 seconds
FIXED_THRESHOLD_PCT = -7   # 🎯 Hard-anchored to exactly -10.0% loss floor

def safe_float(val, fallback=0.0):
    """Prevents runtime float conversion crashes from NaN, None, or empty strings."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return fallback
    try:
        return float(val)
    except (ValueError, TypeError):
        return fallback

def set_cooling(side): 
    """Creates a local timestamp signature file to initiate execution lockout."""
    file_path = f"exebal_cool_{side.lower()}.txt" 
    try:
        with open(file_path, "w") as f: 
            f.write(str(time.time())) 
    except Exception as e:
        print(f"{Fore.RED}⚠️ Cooldown Write Error: {e}")

def is_cooling(side): 
    """Validates if the active option side is currently throttled by the cooling window."""
    file_path = f"exebal_cool_{side.lower()}.txt" 
    if not os.path.exists(file_path): 
        return False 
    try: 
        with open(file_path, "r") as f: 
            content = f.read().strip()
            if not content:
                return False
            last_ts = float(content) 
            if (time.time() - last_ts) < COOL_DOWN_SECONDS: 
                return True 
        try:
            os.remove(file_path) 
        except FileNotFoundError:
            pass
        return False 
    except Exception: 
        return False 

def get_loss(row): 
    """Calculates position loss percentage based on entry and current pricing fields."""
    entry = safe_float(row.get("buy_prc", 0.0)) 
    ltp = safe_float(row.get("sell_prc", 0.0)) 
    return ((ltp - entry) / entry) * 100 if entry > 0 else 0 

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, signal):
    """Renders a clean 42-character width dashboard upon an order routing event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨  PXY® ENGINE SIGNAL HANDOVER  🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " ")) 
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}".ljust(width))
    print(Fore.WHITE + f" • SIDE OPTION   : {side}".ljust(width))
    print(Fore.WHITE + f" • ACTIVE SIGNAL : {signal}".ljust(width))
    
    loss_str = f" • LAST LAYER LSS: {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • LAST LAYER LSS: " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • TARGET THRESH : {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • TARGET THRESH : " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(Fore.WHITE + " • TAG STATUS    : MANAGED BY EXEFORCE".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Strictly processes position tracking and layering based on upstream signal cascades.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)): 
        return 

    # Dynamic column scan to safely catch signals across upstream variations
    last_row = df.iloc[-1]
    raw_entry_signal = "NONE"
    
    for col in ["final_signal", "entry", "pxy_signal"]:
        if col in last_row:
            raw_entry_signal = str(last_row[col]).upper().strip()
            break
            
    # 🛑 EXCLUSIVE FILTER GATEWAY: Take the average ONLY if the signal is exactly OTMBUY or OTMSELL
    if raw_entry_signal not in ["OTMBUY", "OTMSELL"]:
        return

    # Separate processing copy cleanly
    df = df.copy()
    if 'symbol' not in df.columns:
        return
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # --- EXPLICIT SIGNAL SANITY FILTER ---
        current_signal = "NONE"

        if side == 'CE' and raw_entry_signal == "OTMBUY":
            current_signal = "BUY"
        elif side == 'PE' and raw_entry_signal == "OTMSELL":
            current_signal = "SELL"

        if current_signal == "NONE":
            continue

        all_positions_crossed_threshold = True
        
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            # If ANY open layer hasn't dropped past -10.0% yet, block execution
            if pos_loss > FIXED_THRESHOLD_PCT:
                all_positions_crossed_threshold = False
                break  

        if all_positions_crossed_threshold: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                final_loss = get_loss(last_order)
                
                print_pxy_trigger_dashboard(side, symbol, final_loss, FIXED_THRESHOLD_PCT, current_signal)
                
                try: 
                    cli_param = "1" if side == "CE" else "2"
                    target_script = Path(__file__).resolve().parent / "exeforcepxy.py"
                    
                    if target_script.exists():
                        print(f"{Fore.YELLOW}🔄 Routing task to {target_script.name} with parameter [{cli_param}]...")
                        subprocess.run([sys.executable, str(target_script), cli_param], check=True)
                        set_cooling(side) 
                        print(f"{Fore.GREEN}✅ SUCCESS: Handover complete for side {side}.") 
                    else:
                        print(f"{Fore.RED}❌ File Check Error: Script not found at {target_script}")
                        
                except subprocess.CalledProcessError as sub_err:
                    print(f"{Fore.RED}❌ Runtime Execution Error inside exeforcepxy: {sub_err}")
                except Exception as e: 
                    print(f"{Fore.RED}❌ System Automation Handover Failed: {e}")


