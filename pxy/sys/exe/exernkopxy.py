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

# 🔍 Explicit path routing to establish the system footprint layout
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# CONFIGURABLE FILE PATHS (Directly mapped to your LILO dumped outputs)
PNL_JSON_PATH = os.path.abspath(os.path.join(current_dir, "../web/webpnlpxy.json"))
POS_JSON_PATH = os.path.abspath(os.path.join(current_dir, "../web/webpospxy.json"))

# 💾 WEB INTERFACE AND SESSION MEMORY STATE PATH
RENKO_STATE_FILE = os.path.abspath(os.path.join(current_dir, "../web/webrinkopxy.json"))

# RISK METRICS
TRAILING_DROP_LIMIT = 3000.0  # Absolute Rupee drop allowed from the absolute peak
LOOP_INTERVAL_SECONDS = 1.0   # 1-second background polling cycle
EMERGENCY_RETRY_SECONDS = 5.0 # Repeat interval if threshold is hit


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
    """Blocks execution until exactly 09:30 AM IST, then performs a clean historical data wipe."""
    IST = pytz.timezone("Asia/Kolkata")
    has_cleaned_history = False

    while not has_cleaned_history:
        now_ist = datetime.now(IST)
        if now_ist.hour < 9 or (now_ist.hour == 9 and now_ist.minute < 30):
            sys.stdout.write(
                f"\r⏳ {Fore.YELLOW}TIME GATE ACTIVE: System locked until 09:30:00 AM IST. "
                f"Current Time: {now_ist.strftime('%H:%M:%S')}{Style.RESET_ALL}    "
            )
            sys.stdout.flush()
            time.sleep(1.0)
        else:
            print(f"\n\n⏰ {Fore.GREEN}{Style.BRIGHT}⏰ 09:30 AM IST REACHED! COMMENCING MORNING RISK PURGE...")
            save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
            print(f"🧹 {Fore.CYAN}Cleaned up historical cache file: {RENKO_STATE_FILE}")
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
            # 1. Read running and booked performance pools directly from LILO dumps
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
            
            # 6. Stream continuous running data telemetry to the terminal console
            sys.stdout.write(
                f"\r📊 PnL Net: {Fore.YELLOW}₹{current_net_pnl:,.2f}{Style.RESET_ALL} | "
                f"Peak: {Fore.GREEN}₹{session_peak_pnl:,.2f}{Style.RESET_ALL} | "
                f"Exit Trigger Floor: {Fore.RED}₹{active_exit_line:,.2f}{Style.RESET_ALL}    "
            )
            sys.stdout.flush()
            
            # 7. 🔥 CORE CONDITION LOOP RULES EVALUATION
            if current_net_pnl <= active_exit_line:
                # 🚨 THRESHOLD IS HIT: Lock inside this execution block. DO NOT EXIT THE LOOP.
                print(f"\n\n{Fore.RED}{Style.BRIGHT}🚨 TRAILING STOP BREAKER TRIPPED! entering persistent emergency loop...")
                
                script_path = os.path.join(current_dir, "exesqrpxy.py")
                
                # Persistent emergency cycle repeats here forever until manually stopped or positions clear
                while True:
                    print(f"⚡ [{time.strftime('%H:%M:%S')}] {Fore.MAGENTA}Firing emergency square-off script subprocess...")
                    try:
                        if os.path.exists(script_path):
                            # Executes the self-running script with unconditional exit flag
                            subprocess.run(["python3", script_path, "-all"], stdout=sys.stdout, stderr=sys.stderr)
                        else:
                            print(f"{Fore.RED}❌ Square-off script missing at: {script_path}")
                    except Exception as err:
                        print(f"{Fore.RED}❌ Subprocess routing failure: {err}")
                    
                    # Force hard flush to zero inside the web file on every loop pass
                    save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                    
                    # ⏱️ 5-Second persistent retry interval holding parameter
                    print(f"⏳ {Fore.YELLOW}Emergency step complete. Holding loop. Re-firing in {EMERGENCY_RETRY_SECONDS} seconds...\n")
                    time.sleep(EMERGENCY_RETRY_SECONDS)
            
            else:
                # ✅ THRESHOLD NOT HIT: Break the current iteration loop pass cleanly as requested
                # This drops processing out of this specific block to refresh your variables
                pass
                
            time.sleep(LOOP_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⏹ Trailing monitoring execution suspended by user.")
            break
        except Exception as e:
            time.shape(LOOP_INTERVAL_SECONDS)
            continue


if __name__ == "__main__":
    start_trailing_engine()
