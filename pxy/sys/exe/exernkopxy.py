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

# 🛡️ GLOBAL OPERATIONAL SWITCH CONFIGURATION
EXECUTE_SQUARE_OFF = True # LIVE PROTECTION ACTIVATED

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
SQUAREOFF_LOG_FILE = os.path.abspath(os.path.join(current_dir, "../../web/websqrpxy.json"))

# RISK CONFIGURATION CONSTANTS
EMERGENCY_RETRY_SECONDS = 5.0
LOOP_INTERVAL_SECONDS = 1.0

# 🔄 SURGICAL PROXY: Declares the variable locally but pulls values dynamically
import exemeltpxy

class DynamicFloatProxy:
    def __float__(self): return float(exemeltpxy.get_dynamic_trailing_drop())
    def __sub__(self, other): return float(self) - float(other)
    def __rsub__(self, other): return float(other) - float(self)
    def __lt__(self, other): return float(self) < float(other)
    def __le__(self, other): return float(self) <= float(other)
    def __gt__(self, other): return float(self) > float(other)
    def __ge__(self, other): return float(self) >= float(other)
    def __neg__(self): return -float(self)
    def __truediv__(self, other): return float(self) / float(other)
    def __str__(self): return str(float(self))
    def __repr__(self): return str(float(self))
    def __format__(self, format_spec): return format(float(self), format_spec)

# This explicitly defines the name for the compiler so your downstream code doesn't crash
TRAILING_DROP_LIMIT = DynamicFloatProxy()



def safe_load_json_pnl(file_path):
    """Safely extracts cumulative metrics. Rejects data and returns 0.0 if the file timestamp belongs to a previous day. """
    if not os.path.exists(file_path):
        return 0.0
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(IST)
        today_str = now_ist.strftime("%Y-%m-%d")
        
        # 🕒 Check file modification date
        file_mod_timestamp = os.path.getmtime(file_path)
        file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
        
        # 🛑 If file date does not match today, treat as 0.0 to prevent stale carries
        if file_mod_date_str != today_str:
            sys.stdout.write(
                f"\r⚠️ {Fore.YELLOW}STALE DATA BLOCKED: {os.path.basename(file_path)} "
                f"is from {file_mod_date_str}. Assuming 0.0 until updated today.{Style.RESET_ALL}\n"
            )
            sys.stdout.flush()
            return 0.0
            
        # 📄 Proceed to read file if it has today's date
        with open(file_path, "r") as f:
            content = f.read().strip()
            if not content:
                return 0.0
            data = json.loads(content)
            
        if isinstance(data, list):
            total_pnl = 0.0
            for row in data:
                if not isinstance(row, dict):
                    continue
                val = row.get("PNL") or row.get("pnl") or row.get("unrealized") or row.get("realized") or 0.0
                total_pnl += float(val)
            return total_pnl
        elif isinstance(data, dict):
            val = data.get("PNL") or data.get("pnl") or data.get("total_pnl") or 0.0
            return float(val)
        return 0.0
    except Exception as e:
        print(f"{Fore.RED}⚠️ Critical Parse Error on {os.path.basename(file_path)}: {e}")
        return 0.0

def load_session_state():
    if not os.path.exists(RENKO_STATE_FILE):
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -TRAILING_DROP_LIMIT}
    try:
        with open(RENKO_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -TRAILING_DROP_LIMIT}

def save_session_state(peak_value, current_net, exit_line):
    try:
        os.makedirs(os.path.dirname(RENKO_STATE_FILE), exist_ok=True)
        
        # --- FIXED: Explicitly force Indian Standard Time to prevent day-rollover bugs ---
        ist_tz = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist_tz)
        
        payload = {
            "session_peak_pnl": float(peak_value),
            "current_net_pnl": float(current_net),
            "active_exit_line": float(exit_line),
            "updated_timestamp": now_ist.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(RENKO_STATE_FILE, "w") as f:
            json.dump(payload, f, indent=4)
    except Exception as e:
        print(f"{Fore.RED}⚠️ Web State Sync Error: {e}")

def verify_and_purge_stale_cache():
    """Instantly clears stale web files if their update dates don't match today's date."""
    IST = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")
    
    state = load_session_state()
    last_update_time = state.get("updated_timestamp", "")
    
    if today_str not in last_update_time:
        print(f"\n⏰ {Fore.GREEN}{Style.BRIGHT}NEW TRADING DAY DETECTED! RUNNING INSTANT DATA PURGE...")
        
        # Purge files including the new square-off tracker file for target_file_path in [PNL_JSON_PATH, POS_JSON_PATH, SQUAREOFF_LOG_FILE]:
        for target_file_path in [PNL_JSON_PATH, POS_JSON_PATH, SQUAREOFF_LOG_FILE]:
            if os.path.exists(target_file_path):
                file_mod_timestamp = os.path.getmtime(target_file_path)
                file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
                if file_mod_date_str != today_str:
                    print(f"⚠️ {Fore.YELLOW}STALE FILE DETECTED: {os.path.basename(target_file_path)} belongs to yesterday ({file_mod_date_str}).")
                    try:
                        with open(target_file_path, "w") as fw:
                            json.dump([], fw)
                        print(f"🧹 {Fore.GREEN}Successfully purged stale data from {os.path.basename(target_file_path)}.")
                    except Exception as file_err:
                        print(f"{Fore.RED}❌ Error clearing stale file: {file_err}")
                        
        # Peak explicitly reset to 0.0 on morning purge
        save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
        print(f"🧹 {Fore.CYAN}Cleaned up tracking cache file: {RENKO_STATE_FILE}\n")

from datetime import datetime
import pytz

def write_squareoff_success_log():
    """Generates a tracking timestamp payload confirming positions are completely cleared in IST."""
    try:
        os.makedirs(os.path.dirname(SQUAREOFF_LOG_FILE), exist_ok=True)
        # --- FIXED: Explicitly force Indian Standard Time ---
        ist_tz = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist_tz)
        log_payload = {
            "status": "SUCCESSFUL_SQUARE_OFF_CONFIRMED",
            "date": now_ist.strftime('%Y-%m-%d'),
            "successful_time": now_ist.strftime('%H:%M:%S'),
            "unix_timestamp": int(now_ist.timestamp()) # Unix time is inherently global UTC
        }
        with open(SQUAREOFF_LOG_FILE, "w") as fw:
            json.dump(log_payload, fw, indent=4)
        print(f"💾 {Fore.GREEN}Success entry documented in: {os.path.basename(SQUAREOFF_LOG_FILE)}")
    except Exception as e:
        print(f"{Fore.RED}❌ Error writing square-off log: {e}")
def start_trailing_engine():
    """Monitors live data boundaries and executes targeted output grepping when limits are hit."""
    verify_and_purge_stale_cache()

    initial_state = load_session_state()
    session_peak_pnl = float(initial_state.get("session_peak_pnl", 0.0))
    
    try:
        realised_pnl = safe_load_json_pnl(PNL_JSON_PATH)
        unrealised_pnl = safe_load_json_pnl(POS_JSON_PATH)
        current_net_pnl = realised_pnl + unrealised_pnl
        
        # Shift peak upwards dynamically if cumulative returns hit new records
        if current_net_pnl > session_peak_pnl:
            session_peak_pnl = current_net_pnl
            
        active_exit_line = session_peak_pnl - TRAILING_DROP_LIMIT
        save_session_state(session_peak_pnl, current_net_pnl, active_exit_line)
        
        sign_prefix = "+" if active_exit_line > 0 else ""
        exit_display_str = "0.0k" if active_exit_line == 0 else f"{sign_prefix}{active_exit_line / 1000.0:.1f}k"
        
        # Determine the color for Net PnL dynamically
        net_color = Fore.GREEN if current_net_pnl >= 0 else Fore.RED
        
        print(
            f"Exit@{Fore.WHITE}{Style.BRIGHT}{exit_display_str}{Style.RESET_ALL} | "
            f"📊 Net:{net_color}₹{current_net_pnl:,.0f}{Style.RESET_ALL} | "
            f"Peak@{Fore.WHITE}₹{session_peak_pnl:,.0f}{Style.RESET_ALL}"
        )

        # -------- TRIGGER AND BREAK LOGIC TIMELINE --------
        if current_net_pnl <= active_exit_line:
            if EXECUTE_SQUARE_OFF:
                print(f"\n🚨 {Fore.RED}{Style.BRIGHT}LOSS TRIGGER BREACHED! Entering live confirmation verification loop...")
                script_path = os.path.join(current_dir, "exesqrpxy.py")
                
                # Dynamic Environment Fallback: Automatically falls back if environment maps path uniquely
                python_executable = sys.executable if sys.executable else "python"
                
                no_active_positions_counter = 0
                
                # 🔄 RUN FOREVER LOGIC: Continuously validates positions drop to zero
                while True:
                    print(f"⚡ [{time.strftime('%H:%M:%S')}] {Fore.MAGENTA}Firing: {python_executable} exesqrpxy.py -all")
                    
                    if os.path.exists(script_path):
                        try:
                            # Run the process with the "-all" argument and capture text outputs
                            process = subprocess.Popen(
                                [python_executable, script_path, "-all"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                bufsize=1
                            )
                            
                            found_phrase_in_this_run = False
                            
                            # Stream live console outputs line-by-line
                            for line in process.stdout:
                                sys.stdout.write(line)
                                sys.stdout.flush()
                                
                                # Grep target confirmation phrase
                                if "No active positions to exit" in line:
                                    found_phrase_in_this_run = True
                            
                            process.wait()
                            
                            # Increment or reset the confirmation safety counter
                            if found_phrase_in_this_run:
                                no_active_positions_counter += 1
                                print(f"🎯 {Fore.CYAN}Grep Match Verified! Count: ({no_active_positions_counter}/3)")
                            else:
                                no_active_positions_counter = 0  # Broken chain reset
                                
                            # Exit loop and close engine cleanly when 3 consecutive confirmations match
                            if no_active_positions_counter >= 3:
                                print(f"\n✅ {Fore.GREEN}{Style.BRIGHT}TRIPLE MATCH CONFIRMED: No positions remain active.")
                                write_squareoff_success_log()
                                # Peak explicitly reset to 0.0 here upon final confirmed exit
                                save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                                sys.exit(0)
                                
                        except Exception as proc_err:
                            print(f"{Fore.RED}❌ Process routing engine error: {proc_err}")
                            no_active_positions_counter = 0
                    else:
                        print(f"{Fore.RED}❌ Square-off script missing at: {script_path}")
                    
                    # Peak explicitly reset to 0.0 here during loop retry passes
                    save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                    print(f"⏳ {Fore.YELLOW}Retry pass complete. Re-checking loop in {EMERGENCY_RETRY_SECONDS} seconds...\n")
                    time.sleep(EMERGENCY_RETRY_SECONDS)
            else:
                print(f"\n⚠️ {Fore.YELLOW}{Style.BRIGHT}WARNING TARGET BREACHED: Threshold line {exit_display_str} violated!")
                sys.exit(0)
        else:
            # ✅ BREAK ENGINE OUT: Safe condition verified. Return control to shell loop supervisor.
            sys.exit(0)

    except Exception as e:
        print(f"{Fore.RED}Execution Error inside tracker engine: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_trailing_engine()
