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
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds
FIXED_THRESHOLD_PCT = -10.0  # 🎯 Hard-anchored to exactly -10.0% loss floor

def safe_float(val, fallback=0.0):
    """Prevents runtime float conversion crashes from NaN, None, or empty strings."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return fallback
    try:
        return float(val)
    except (ValueError, TypeError):
        return fallback

def set_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    try:
        with open(file_path, "w") as f: 
            f.write(str(time.time())) 
    except Exception as e:
        print(f"{Fore.RED}⚠️ Cooldown Write Error: {e}")

def is_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    if not os.path.exists(file_path): 
        return False 
    try: 
        with open(file_path, "r") as f: 
            last_ts = float(f.read().strip()) 
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
    """Optimized globally to prevent memory re-allocation inside the loop."""
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
    """Strictly processes position tracking ONLY on active exit column BUY or SELL signals.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)): 
        return 

    if "exit" not in df.columns:
        return
        
    last_row = df.iloc[-1]
    raw_exit_signal = str(last_row["exit"]).upper().strip() 

    # 🛑 CRITICAL INTERCEPT DOOR: Stop dead if the exit signal isn't EXACTLY BUY or SELL
    if raw_exit_signal not in ["BUY", "SELL"]:
        return

    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # --- EXPLICIT SIGNAL SANITY FILTER FROM EXIT COLUMN ---
        current_signal = "NONE"

        # CE side acts ONLY if the exit column is pumping "BUY"
        if side == 'CE' and raw_exit_signal == "BUY":
            current_signal = "BUY"

        # PE side acts ONLY if the exit column is pumping "SELL"
        elif side == 'PE' and raw_exit_signal == "SELL":
            current_signal = "SELL"

        # If this option chain side does not mirror the live trigger, skip instantly
        if current_signal == "NONE":
            continue

        # Start with assumption that it's safe to fire
        all_positions_crossed_threshold = True
        
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            # 🔄 MATHEMATICAL VERIFICATION:
            # If ANY position is safer than -10% (e.g., -4.5% > -10.0%), 
            # then NOT all positions are down past the threshold. Fail and break.
            if pos_loss > FIXED_THRESHOLD_PCT:
                all_positions_crossed_threshold = False
                break  

        loss_hit = all_positions_crossed_threshold

        if loss_hit: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                final_loss = get_loss(last_order)
                
                # Render clean notification box before handover execution
                print_pxy_trigger_dashboard(side, symbol, final_loss, FIXED_THRESHOLD_PCT, current_signal)
                
                # --- AUTOMATED PARAMETER HANDOFF TO EXEFORCE PXY ---
                try: 
                    # Parameter "1" maps to CE (BUY), Parameter "2" maps to PE (SELL)
                    cli_param = "1" if side == "CE" else "2"
                    
                    target_script = Path(__file__).resolve().parent / "exeforcepxy.py"
                    
                    if target_script.exists():
                        print(f"{Fore.YELLOW}🔄 Routing task to {target_script.name} with parameter [{cli_param}]...")
                        
                        # Runs: python exeforcepxy.py 1 (or 2)
                        subprocess.run([sys.executable, str(target_script), cli_param], check=True)
                        
                        set_cooling(side) 
                        print(f"{Fore.GREEN}✅ SUCCESS: Handover complete for side {side}.") 
                    else:
                        print(f"{Fore.RED}❌ File Check Error: Script not found at {target_script}")
                        
                except subprocess.CalledProcessError as sub_err:
                    print(f"{Fore.RED}❌ Runtime Execution Error inside exeforcepxy: {sub_err}")
                except Exception as e: 
                    print(f"{Fore.RED}❌ System Automation Handover Failed: {e}")

