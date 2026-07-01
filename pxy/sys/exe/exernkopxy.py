# V1L58/pxy/sys/exe/exernkopxy.py
import os
import sys
import json
import time
import subprocess
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# 🛡️ GLOBAL OPERATIONAL SWITCH CONFIGURATION
EXECUTE_SQUARE_OFF = False  

# 🔍 STRATEGIC FOOTPRINT: Explicit path isolation handling
current_dir = os.path.dirname(os.path.abspath(__file__))
run_dir = os.path.join(current_dir, "run")

if current_dir not in sys.path:
    sys.path.append(current_dir)
if run_dir not in sys.path:
    sys.path.append(run_dir)

# CONFIGURABLE FILE PATHS
PNL_JSON_PATH = os.path.abspath(os.path.join(current_dir, "../../web/webpnlpxy.json"))
POS_JSON_PATH = os.path.abspath(os.path.join(current_dir, "../../web/webpospxy.json"))
RENKO_STATE_FILE = os.path.abspath(os.path.join(current_dir, "../../web/webrinkopxy.json"))

# RISK CONFIGURATION CONSTANTS
TRAILING_DROP_LIMIT = 3000.0  
EMERGENCY_RETRY_SECONDS = 5.0 
LOOP_INTERVAL_SECONDS = 1.0   


def safe_load_json_pnl(file_path):
    if not os.path.exists(file_path):
        return 0.0
    try:
        with open(file_path, "r") as f:
            content = f.read().strip()
            if not content:
                return 0.0
            data = json.loads(content)
        if isinstance(data, list):
            return sum(float(row.get("PNL", 0.0)) for row in data)
        return 0.0
    except Exception:
        return 0.0


def load_session_state():
    if not os.path.exists(RENKO_STATE_FILE):
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -3000.0}
    try:
        with open(RENKO_STATE_FILE, "r") as f:
            state = json.load(f)
            return state
    except Exception:
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -3000.0}


def save_session_state(peak_value, current_net, exit_line):
    try:
        os.makedirs(os.path.dirname(RENKO_STATE_FILE), exist_ok=True)
        payload = {
            "session_peak_pnl": float(peak_value),
            "current_net_pnl": float(current_net),
            "active_exit_line": float(exit_line),
            "updated_timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(RENKO_STATE_FILE, "w") as f:
            json.dump(payload, f, indent=4)
    except Exception as e:
        print(f"{Fore.RED}⚠ Web State Sync Error: {e}")


def enforce_morning_time_gate():
    """Rigidly structures the morning constraints timeline.
    
    00:00 AM - 08:59 AM IST: Wait passively (Market hasn't opened setup windows)
    09:00 AM - 09:29 AM IST: Hard lockout time gate active
    09:30 AM IST onwards    : Performs clean sweep once and opens tracking loops
    """
    IST = pytz.timezone("Asia/Kolkata")
    has_cleaned_history = False

    while not has_cleaned_history:
        now_ist = datetime.now(IST)
        now_time = now_ist.time()
        
        # Define strict absolute boundary markers
        gate_start = dt_time(9, 0, 0)
        gate_end = dt_time(9, 16, 0)
        
        # 🛡️ PHASE 1: Pre-9:00 AM Early Morning Holding Pattern
        if now_time < gate_start:
            sys.stdout.write(
                f"\r⏳ {Fore.CYAN} HOLD"
                f"  Current Time: {now_ist.strftime('%H:%M:%S')}{Style.RESET_ALL}    "
            )
            sys.stdout.flush()
            time.sleep(1.0)
            
        # 🛡️ PHASE 2: 09:00 AM to 09:29:59 AM Strict Time Gate Lockout
        elif gate_start <= now_time < gate_end:
            sys.stdout.write(
                f"\r⏳ {Fore.YELLOW}TIME GATE ACTIVE: System locked from 09:00 to 09:16 AM IST. "
                f"Current Time: {now_ist.strftime('%H:%M:%S')}{Style.RESET_ALL}    "
            )
            sys.stdout.flush()
            time.sleep(1.0)
            
        # 🛡️ PHASE 3: 09:30:00 AM or Later -> Execute Cleanup once and break out
        else:
            state = load_session_state()
            last_update_time = state.get("updated_timestamp", "")
            today_str = now_ist.strftime("%Y-%m-%d")
            
            if today_str not in last_update_time:
                print(f"\n\n⏰ {Fore.GREEN}{Style.BRIGHT}09:30 AM IST PASSED! RUNNING MORNING DATA PURGE...")
                
                for target_file_path in [PNL_JSON_PATH, POS_JSON_PATH]:
                    if os.path.exists(target_file_path):
                        file_mod_timestamp = os.path.getmtime(target_file_path)
                        file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
                        
                        if file_mod_date_str != today_str:
                            print(f"⚠️  {Fore.YELLOW}STALE FILE DETECTED: {os.path.basename(target_file_path)} belongs to yesterday ({file_mod_date_str}).")
                            try:
                                with open(target_file_path, "w") as fw:
                                    json.dump([], fw)
                                print(f"🧹 {Fore.GREEN}Successfully purged stale data from {os.path.basename(target_file_path)}.")
                            except Exception as file_err:
                                print(f"{Fore.RED}❌ Error clearing stale file: {file_err}")
                
                save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                print(f"🧹 {Fore.CYAN}Cleaned up tracking cache file: {RENKO_STATE_FILE}\n")
            
            has_cleaned_history = True


def start_trailing_engine():
    enforce_morning_time_gate()

    initial_state = load_session_state()
    session_peak_pnl = float(initial_state.get("session_peak_pnl", 0.0))
    
    try:
        realised_pnl = safe_load_json_pnl(PNL_JSON_PATH)
        unrealised_pnl = safe_load_json_pnl(POS_JSON_PATH)
        current_net_pnl = realised_pnl + unrealised_pnl
        
        if current_net_pnl > session_peak_pnl:
            session_peak_pnl = current_net_pnl
            
        active_exit_line = session_peak_pnl - TRAILING_DROP_LIMIT
        save_session_state(session_peak_pnl, current_net_pnl, active_exit_line)
        
        sign_prefix = "+" if active_exit_line > 0 else ""
        if active_exit_line == 0:
            exit_display_str = "0.0k"
        else:
            exit_display_str = f"{sign_prefix}{active_exit_line / 1000.0:.1f}k"
        
        print(
            f"Exit@{Fore.RED}₹{Style.BRIGHT}{exit_display_str}{Style.RESET_ALL} |"
            f"📊 Net:{Fore.GREEN}₹{current_net_pnl:,.0f}{Style.RESET_ALL} | "
            f"Peak@{Fore.YELLOW}₹{session_peak_pnl:,.0f}{Style.RESET_ALL} "

        )
        
        # -------- TRIGGER AND BREAK LOGIC TIMELINE --------
        if current_net_pnl <= active_exit_line:
            if EXECUTE_SQUARE_OFF:
                print(f"\n🚨 {Fore.RED}{Style.BRIGHT}LOSS TRIGGER BREACHED (Net ₹{current_net_pnl:,.0f} <= Limit {exit_display_str})! Entering persistent emergency loop...")
                script_path = os.path.join(current_dir, "exesqrpxy.py")
                
                # 🔄 RUN FOREVER LOGIC: This block runs continuously if triggered
                while True:
                    print(f"⚡ [{time.strftime('%H:%M:%S')}] {Fore.MAGENTA}Firing emergency square-off subprocess...")
                    try:
                        if os.path.exists(script_path):
                            subprocess.run(["python3", script_path, "-all"], stdout=sys.stdout, stderr=sys.stderr)
                        else:
                            print(f"{Fore.RED}❌ Square-off script missing at: {script_path}")
                    except Exception as err:
                        print(f"{Fore.RED}❌ Subprocess routing failure: {err}")
                    
                    save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                    print(f"⏳ {Fore.YELLOW}Retry pass complete. Re-firing in {EMERGENCY_RETRY_SECONDS} seconds...\n")
                    time.sleep(EMERGENCY_RETRY_SECONDS)
            else:
                print(f"\n⚠️  {Fore.YELLOW}{Style.BRIGHT}⚠️  WARNING TARGET BREACHED: Net dropped below floor threshold {exit_display_str}!")
                sys.exit(0)
        else:
            # ✅ BREAK ENGINE OUT: Safe condition verified. Clean exit returns control to your main supervisor.
            sys.exit(0)

    except Exception as e:
        print(f"{Fore.RED}Execution Error inside tracker engine: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_trailing_engine()
