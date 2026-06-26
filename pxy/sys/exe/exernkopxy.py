# V1L58/pxy/sys/exe/exernkopxy.py
import os
import sys
import json
import time
import subprocess
import pytz
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# 🔍 STRATEGIC FOOTPRINT: Explicit path isolation handling
current_dir = os.path.dirname(os.path.abspath(__file__))
run_dir = os.path.join(current_dir, "run")

if current_dir not in sys.path:
    sys.path.append(current_dir)
if run_dir not in sys.path:
    sys.path.append(run_dir)

# CONFIGURABLE FILE PATHS (Surgically aligned to your true directory architecture)
PNL_JSON_PATH = os.path.abspath(os.path.join(current_dir, "../../web/webpnlpxy.json"))
POS_JSON_PATH = os.path.abspath(os.path.join(current_dir, "../../web/webpospxy.json"))

# 💾 WEB DASHBOARD PERSISTENT DATA INTERFACE NODE
RENKO_STATE_FILE = os.path.abspath(os.path.join(current_dir, "../../web/webrinkopxy.json"))

# RISK CONFIGURATION CONSTANTS
TRAILING_DROP_LIMIT = 3000.0  # Absolute Rupee drawdown allowed from the peak
LOOP_INTERVAL_SECONDS = 1.0   # 1-second interval execution tracking speed
EMERGENCY_RETRY_SECONDS = 5.0 # Repeat interval if threshold is breached


def safe_load_json_pnl(file_path):
    """Safely extracts and sums PNL values from LILO dumped JSON telemetry files."""
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
    """Recovers the active session peak and configurations from the web interface JSON file."""
    if not os.path.exists(RENKO_STATE_FILE):
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -3000.0}
    try:
        with open(RENKO_STATE_FILE, "r") as f:
            state = json.load(f)
            return state
    except Exception:
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -3000.0}


def save_session_state(peak_value, current_net, exit_line):
    """Saves the complete risk metrics matrix to the web json folder for UI rendering."""
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
    """Blocks execution from 09:00:00 AM to 09:30:00 AM IST.

    Validates file age at 09:30 AM and wipes historical files if stale.
    """
    IST = pytz.timezone("Asia/Kolkata")
    has_cleaned_history = False

    while not has_cleaned_history:
        now_ist = datetime.now(IST)
        
        # ⏱️ TIME GATE BOUNDARY LOCK: 09:00 AM to 09:30 AM
        if 9 <= now_ist.hour < 10 and now_ist.minute < 30:
            sys.stdout.write(
                f"\r⏳ {Fore.YELLOW}TIME GATE ACTIVE: System locked from 09:00 to 09:30 AM IST. "
                f"Current Time: {now_ist.strftime('%H:%M:%S')}{Style.RESET_ALL}    "
            )
            sys.stdout.flush()
            time.sleep(1.0)
        else:
            print(f"\n\n⏰ {Fore.GREEN}{Style.BRIGHT}09:30 AM IST REACHED! COMMENCING MORNING DATA VERIFICATION...")
            
            # 🛡️ SURGICAL SOURCE FILE DATE CHECK
            today_date_str = now_ist.strftime("%Y-%m-%d")
            
            for target_file_path in [PNL_JSON_PATH, POS_JSON_PATH]:
                if os.path.exists(target_file_path):
                    # Extract the absolute last modified timestamp from the filesystem
                    file_mod_timestamp = os.path.getmtime(target_file_path)
                    file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
                    
                    # If file date doesn't match today's date string, it is stale data from yesterday
                    if file_mod_date_str != today_date_str:
                        print(f"⚠️  {Fore.YELLOW}STALE FILE DETECTED: {os.path.basename(target_file_path)} belongs to yesterday ({file_mod_date_str}).")
                        try:
                            # Force overwrite file to an absolute blank JSON array
                            with open(target_file_path, "w") as fw:
                                json.dump([], fw)
                            print(f"🧹 {Fore.GREEN}Successfully purged stale data from {os.path.basename(target_file_path)}.")
                        except Exception as file_err:
                            print(f"{Fore.RED}❌ Error clearing stale file: {file_err}")
            
            # Flush trailing tracking parameters completely back to ground zero
            save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
            print(f"🧹 {Fore.CYAN}Cleaned up tracking cache file: {RENKO_STATE_FILE}")
            print(f"✅ {Fore.GREEN}System parameters fully initialized. Launching Trailing Engine Matrix Loops!\n")
            has_cleaned_history = True


def start_trailing_engine():
    # ⏱️ Activate Time and History Gate immediately upon system startup
    enforce_morning_time_gate()

    # 🔄 Load freshly cleaned state matrix directly from the web dashboard tracking file
    initial_state = load_session_state()
    session_peak_pnl = float(initial_state.get("session_peak_pnl", 0.0))
    
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 High-Resolution Conditional Breaking Trailing Engine Live.")
    print(f"Tracking UI Sync File: {Fore.WHITE}{RENKO_STATE_FILE}\n")

    while True:
        try:
            # 1. Read running and booked performance pools directly from clean dumps
            realised_pnl = safe_load_json_pnl(PNL_JSON_PATH)
            unrealised_pnl = safe_load_json_pnl(POS_JSON_PATH)
            
            # 2. Combine values to generate accurate, real-time live portfolio performance
            current_net_pnl = realised_pnl + unrealised_pnl
            
            # 3. Maintain High-Water Mark: Updates continuously on every single rupee increase
            if current_net_pnl > session_peak_pnl:
                session_peak_pnl = current_net_pnl
                
            # 4. Compute the active trailing exit trigger line dynamically from your absolute peak
            active_exit_line = session_peak_pnl - TRAILING_DROP_LIMIT
            
            # 5. Persist the complete metrics matrix out to your web dashboard tracking file
            save_session_state(session_peak_pnl, current_net_pnl, active_exit_line)
            
            # 6. Stream continuous running data telemetry to the console
            sys.stdout.write(
                f"\r📊 PnL Net: {Fore.YELLOW}₹{current_net_pnl:,.2f}{Style.RESET_ALL} | "
                f"Peak: {Fore.GREEN}₹{session_peak_pnl:,.2f}{Style.RESET_ALL} | "
                f"Exit Floor: {Fore.RED}₹{active_exit_line:,.2f}{Style.RESET_ALL} | "
                f"Loss Trigger: {Fore.RED}{Style.BRIGHT}₹{active_exit_line:,.2f}{Style.RESET_ALL}    "
            )
            sys.stdout.flush()
            
            # 7. CORE CONDITION LOOP RULES EVALUATION
            if current_net_pnl <= active_exit_line:
                print(f"\n\n{Fore.RED}{Style.BRIGHT}🚨 LOSS TRIGGER BREACHED (Net ₹{current_net_pnl:,.2f} <= Trigger ₹{active_exit_line:,.2f})! Entering persistent emergency loop...")
                
                script_path = os.path.join(current_dir, "exesqrpxy.py")
                
                while True:
                    print(f"⚡ [{time.strftime('%H:%M:%S')}] {Fore.MAGENTA}Firing emergency square-off script subprocess...")
                    try:
                        if os.path.exists(script_path):
                            subprocess.run(["python3", script_path, "-all"], stdout=sys.stdout, stderr=sys.stderr)
                        else:
                            print(f"{Fore.RED}❌ Square-off script missing at: {script_path}")
                    except Exception as err:
                        print(f"{Fore.RED}❌ Subprocess routing failure: {err}")
                    
                    save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                    
                    print(f"⏳ {Fore.YELLOW}Emergency execution pass complete. Holding loop. Re-firing in {EMERGENCY_RETRY_SECONDS} seconds...\n")
                    time.sleep(EMERGENCY_RETRY_SECONDS)
            
            else:
                pass
                
            time.sleep(LOOP_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⏹ Trailing monitoring execution suspended by user.")
            break
        except Exception as e:
            time.sleep(LOOP_INTERVAL_SECONDS)
            continue


if __name__ == "__main__":
    start_trailing_engine()

