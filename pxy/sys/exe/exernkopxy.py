# V1L58/pxy/sys/exe/exernkopxy.py — PART 1 (DEBUG ENABLED)
import os
import sys
import json
import time
import subprocess
import pytz
from datetime import datetime, time as dt_time, timedelta
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

print(f"{Fore.MAGENTA}[DEBUG-BOOT] Initializing System Terminal Color Palette Subsystem...")

# 🛡️ GLOBAL OPERATIONAL SWITCH CONFIGURATION
EXECUTE_SQUARE_OFF = True  
print(f"{Fore.MAGENTA}[DEBUG-BOOT] Hard Safety Circuit Breaker (EXECUTE_SQUARE_OFF): {EXECUTE_SQUARE_OFF}")

# 🔍 STRATEGIC FOOTPRINT: Explicit path isolation handling
current_dir = os.path.dirname(os.path.abspath(__file__))
run_dir = os.path.join(current_dir, "run")
print(f"{Fore.MAGENTA}[DEBUG-BOOT] Isolating Execution Directory Context: {current_dir}")

if current_dir not in sys.path:
    sys.path.append(current_dir)
if run_dir not in sys.path:
    sys.path.append(run_dir)

# CONFIGURABLE FILE PATHS
PNL_JSON_PATH = os.path.abspath(os.path.join(current_dir, "../../web/webpnlpxy.json"))
POS_JSON_PATH = os.path.abspath(os.path.join(current_dir, "../../web/webpospxy.json"))
RENKO_STATE_FILE = os.path.abspath(os.path.join(current_dir, "../../web/webrinkopxy.json"))

print(f"{Fore.MAGENTA}[DEBUG-BOOT] Target PNL Matrix Dataframe Node: {PNL_JSON_PATH}")
print(f"{Fore.MAGENTA}[DEBUG-BOOT] Target Position Matrix Dataframe Node: {POS_JSON_PATH}")
print(f"{Fore.MAGENTA}[DEBUG-BOOT] Core Session Cache JSON File Node: {RENKO_STATE_FILE}")

# RISK CONFIGURATION CONSTANTS
TRAILING_DROP_LIMIT = 3000.0  
EMERGENCY_RETRY_SECONDS = 5.0 
LOOP_INTERVAL_SECONDS = 1.0   
print(f"{Fore.MAGENTA}[DEBUG-BOOT] Static Parameters Locked -> Drop Limit: ₹{TRAILING_DROP_LIMIT} | Retry Cadence: {EMERGENCY_RETRY_SECONDS}s")


def safe_load_json_pnl(file_path):
    print(f"{Fore.BLUE}[DEBUG-IO] Scanning storage sector for node: {os.path.basename(file_path)}")
    if not os.path.exists(file_path):
        print(f"{Fore.RED}[DEBUG-IO] IO Warning: Physical target file not found on disk. Returning fallback baseline 0.0")
        return 0.0
    try:
        with open(file_path, "r") as f:
            content = f.read().strip()
            if not content:
                print(f"{Fore.YELLOW}[DEBUG-IO] IO Notice: Node target buffer contains empty byte stream. Returning 0.0")
                return 0.0
            data = json.loads(content)
        if isinstance(data, list):
            calculated_sum = sum(float(row.get("PNL", 0.0)) for row in data)
            print(f"{Fore.BLUE}[DEBUG-IO] Successfully parsed JSON list array. Calculated total sum value: ₹{calculated_sum:,.2f}")
            return calculated_sum
        print(f"{Fore.YELLOW}[DEBUG-IO] Target does not follow standard structured array rows. Returning 0.0")
        return 0.0
    except Exception as io_err:
        print(f"{Fore.RED}[DEBUG-IO] CRITICAL JSON PARSER CRASH: {io_err}. Supplying safe fallback data 0.0")
        return 0.0


def load_session_state():
    print(f"{Fore.BLUE}[DEBUG-CACHE] Restoring active runtime matrix from: {os.path.basename(RENKO_STATE_FILE)}")
    if not os.path.exists(RENKO_STATE_FILE):
        print(f"{Fore.YELLOW}[DEBUG-CACHE] Engine Cache not found. Provisioning system context defaults...")
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -3000.0}
    try:
        with open(RENKO_STATE_FILE, "r") as f:
            state = json.load(f)
            print(f"{Fore.BLUE}[DEBUG-CACHE] State Hydrated -> Prior Peak: ₹{state.get('session_peak_pnl')}, Floor Line: ₹{state.get('active_exit_line')}")
            return state
    except Exception as state_err:
        print(f"{Fore.RED}[DEBUG-CACHE] Cache corruption detected ({state_err}). Initializing blank safe state structures...")
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
        print(f"{Fore.BLUE}[DEBUG-SYNC] Disk Flush Complete -> State Sync Parameters Flushed into System Storage Matrix.")
    except Exception as e:
        print(f"{Fore.RED}⚠ Web State Sync Error: {e}")
# V1L58/pxy/sys/exe/exernkopxy.py — PART 2 (DEBUG ENABLED)

def enforce_morning_time_gate():
    """Rigidly structures the morning constraints timeline with active debug alerts."""
    IST = pytz.timezone("Asia/Kolkata")
    has_cleaned_history = False

    while not has_cleaned_history:
        now_ist = datetime.now(IST)
        now_time = now_ist.time()
        
        gate_start = dt_time(9, 0, 0)
        gate_end = dt_time(9, 16, 0)
        
        # 🛡️ PHASE 1: Pre-9:00 AM Early Morning Holding Pattern
        if now_time < gate_start:
            sys.stdout.write(
                f"\r⏳ {Fore.CYAN}[DEBUG-GATE: HOLD]"
                f" Current Time: {now_ist.strftime('%H:%M:%S')} | Target Opened: 09:00 AM IST{Style.RESET_ALL}   "
            )
            sys.stdout.flush()
            time.sleep(1.0)
            
        # 🛡️ PHASE 2: 09:00 AM to 09:15:59 AM Strict Time Gate Lockout
        elif gate_start <= now_time < gate_end:
            sys.stdout.write(
                f"\r⏳ {Fore.YELLOW}[DEBUG-GATE: LOCKED]"
                f" System locked from 09:00 to 09:16 AM. Current: {now_ist.strftime('%H:%M:%S')}{Style.RESET_ALL}   "
            )
            sys.stdout.flush()
            time.sleep(1.0)
            
        # 🛡️ PHASE 3: 09:16:00 AM or Later -> Execute Cleanup once and break out
        else:
            print(f"\n{Fore.GREEN}[DEBUG-GATE: UNLOCKED] Temporal checkpoint gate validation passed.")
            state = load_session_state()
            last_update_time = state.get("updated_timestamp", "")
            today_str = now_ist.strftime("%Y-%m-%d")
            
            print(f"{Fore.BLUE}[DEBUG-PURGE] Analyzing historical data stamps. Today: {today_str} | Cache Last Modified: {last_update_time}")
            
            if today_str not in last_update_time:
                print(f"\n⏰ {Fore.GREEN}{Style.BRIGHT}09:16 AM IST PASSED! RUNNING MORNING DATA PURGE...")
                
                for target_file_path in [PNL_JSON_PATH, POS_JSON_PATH]:
                    if os.path.exists(target_file_path):
                        file_mod_timestamp = os.path.getmtime(target_file_path)
                        file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
                        
                        print(f"{Fore.BLUE}[DEBUG-PURGE] Verifying cache validity of {os.path.basename(target_file_path)}: Written date is {file_mod_date_str}")
                        if file_mod_date_str != today_str:
                            print(f"⚠️ {Fore.YELLOW}STALE FILE DETECTED: {os.path.basename(target_file_path)} belongs to yesterday ({file_mod_date_str}).")
                            try:
                                with open(target_file_path, "w") as fw:
                                    json.dump([], fw)
                                print(f"🧹 {Fore.GREEN}Successfully purged stale data from {os.path.basename(target_file_path)}.")
                            except Exception as file_err:
                                print(f"{Fore.RED}❌ Error clearing stale file: {file_err}")
                
                print(f"{Fore.BLUE}[DEBUG-PURGE] Resetting global cache state tracking thresholds to pristine baselines...")
                save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                print(f"🧹 {Fore.CYAN}Cleaned up tracking cache file: {RENKO_STATE_FILE}\n")
            else:
                print(f"{Fore.BLUE}[DEBUG-PURGE] Today's workspace timestamp verified matching the runtime data matrix. Skipping active wipe sequence.")
            
            has_cleaned_history = True


def start_trailing_engine(current_loop_num):
    print(f"\n{Fore.MAGENTA}[DEBUG-ENGINE] Pre-flight initialization validation checks tracking iteration: #{current_loop_num}")
    enforce_morning_time_gate()

    initial_state = load_session_state()
    session_peak_pnl = float(initial_state.get("session_peak_pnl", 0.0))
    print(f"{Fore.MAGENTA}[DEBUG-ENGINE] Loaded active peak reference target threshold: ₹{session_peak_pnl:,.2f}")
    
    try:
        realised_pnl = safe_load_json_pnl(PNL_JSON_PATH)
        unrealised_pnl = safe_load_json_pnl(POS_JSON_PATH)
        current_net_pnl = realised_pnl + unrealised_pnl
        print(f"{Fore.MAGENTA}[DEBUG-ENGINE] Math: Realised (₹{realised_pnl}) + Unrealised (₹{unrealised_pnl}) = Net PNL (₹{current_net_pnl})")
        
        if current_net_pnl > session_peak_pnl:
            print(f"{Fore.GREEN}[DEBUG-ENGINE] 🎉 New peak verified! Advancing peak reference target from ₹{session_peak_pnl} to ₹{current_net_pnl}")
            session_peak_pnl = current_net_pnl
            
        active_exit_line = session_peak_pnl - TRAILING_DROP_LIMIT
        print(f"{Fore.MAGENTA}[DEBUG-ENGINE] Evaluation Matrix Target Allocation Floor Line Set at: ₹{active_exit_line}")
        save_session_state(session_peak_pnl, current_net_pnl, active_exit_line)
        
        sign_prefix = "+" if active_exit_line > 0 else ""
        exit_display_str = "0.0k" if active_exit_line == 0 else f"{sign_prefix}{active_exit_line / 1000.0:.1f}k"
        
        sys.stdout.write(
            f"\r⏳ [{current_loop_num:02d}/20] "
            f"Exit@{Fore.RED}₹{Style.BRIGHT}{exit_display_str}{Style.RESET_ALL} | "
            f"📊 Net:{Fore.GREEN}₹{current_net_pnl:,.0f}{Style.RESET_ALL} | "
            f"Peak@{Fore.YELLOW}₹{session_peak_pnl:,.0f}{Style.RESET_ALL}   "
        )
        sys.stdout.flush()
        
        print(f"\n{Fore.BLUE}[DEBUG-RISK] Running valuation safety bounds test: Is Net PNL (₹{current_net_pnl}) <= Floor Line Limit (₹{active_exit_line})?")
        # -------- TRIGGER AND BREAK LOGIC TIMELINE --------
        if current_net_pnl <= active_exit_line:
            print(f"{Fore.RED}[DEBUG-RISK] CRITICAL BREACH CONFIRMED: Risk thresholds completely exceeded.")
            if EXECUTE_SQUARE_OFF:
                print(f"\n🚨 {Fore.RED}{Style.BRIGHT}LOSS TRIGGER BREACHED (Net ₹{current_net_pnl:,.0f} <= Limit {exit_display_str})! Entering persistent emergency loop...")
                script_path = os.path.join(current_dir, "exesqrpxy.py")
                
                while True:
                    print(f"⚡ [{time.strftime('%H:%M:%S')}] {Fore.MAGENTA}Firing emergency square-off subprocess...")
                    try:
                        if os.path.exists(script_path):
                            print(f"{Fore.BLUE}[DEBUG-SUBPROCESS] Spawning Python Execution Core Subthread: {script_path}")
                            subprocess.run(["python3", script_path, "-all"], stdout=sys.stdout, stderr=sys.stderr)
                        else:
                            print(f"{Fore.RED}❌ Square-off script missing at: {script_path}")
                    except Exception as err:
                        print(f"{Fore.RED}❌ Subprocess routing failure: {err}")
                    
                    save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                    print(f"⏳ {Fore.YELLOW}Retry pass complete. Re-firing in {EMERGENCY_RETRY_SECONDS} seconds...\n")
                    time.sleep(EMERGENCY_RETRY_SECONDS)
            else:
                print(f"\n⚠️ {Fore.YELLOW}{Style.BRIGHT}⚠️ WARNING TARGET BREACHED: Net dropped below floor threshold {exit_display_str}!")
                return
        else:
            print(f"{Fore.GREEN}[DEBUG-RISK] Safety clearance granted. Current risk metrics are within normal parameters.")
            return

    except Exception as e:
        print(f"\n{Fore.RED}Execution Error inside tracker engine: {e}")
        return


if __name__ == "__main__":
    IST = pytz.timezone("Asia/Kolkata")
    loop_count = 0
    print(f"{Fore.MAGENTA}[DEBUG-MAIN] Core Orchestration Main Loop Engine Running. Syncing Clock Frameworks...")
    
    while True:
        loop_count += 1
        print(f"\n{Fore.BLUE}[DEBUG-MAIN] Stepping into tracking pipeline loop counter sequence position: {loop_count}/20")
        start_trailing_engine(loop_count)
        
        # 🎯 Operational Loop Cap Gating Check
        if loop_count >= 20:
            print(f"\n\n🛑 {Fore.YELLOW}Operational Loop Cap Hit (20/20). Calculating next wake-up gate...")
            
            now_ist = datetime.now(IST)
            wake_target = now_ist.replace(hour=9, minute=16, second=0, microsecond=0) + timedelta(days=1)
            print(f"{Fore.MAGENTA}[DEBUG-HIBERNATE] Anchor Baseline Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
            print(f"{Fore.MAGENTA}[DEBUG-HIBERNATE] Target Wake-up Lockout Objective: {wake_target.strftime('%Y-%m-%d %H:%M:%S')} IST")
            
            while True:
                current_time = datetime.now(IST)
                seconds_remaining = int((wake_target - current_time).total_seconds())
                
                if seconds_remaining <= 0:
                    print(f"\n{Fore.GREEN}[DEBUG-HIBERNATE] Sleep countdown target reached. Breaking hibernation state.")
                    break
                    
                hours, remainder = divmod(seconds_remaining, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                sys.stdout.write(
                    f"\r🛌 {Fore.CYAN}HIBERNATING until 09:16 AM IST tomorrow. "
                    f"Time Remaining: {hours:02d}h {minutes:02d}m {seconds:02d}s {Style.RESET_ALL}"
                )
                sys.stdout.flush()
                time.sleep(1.0)
            
            print(f"\n⏰ {Fore.GREEN}Waking up! Resetting core engine iteration parameters for the new session.\n")
            loop_count = 0
                
        print(f"{Fore.BLUE}[DEBUG-MAIN] Cycle done. Sleeping for base interval parameter delay: {LOOP_INTERVAL_SECONDS}s")
        time.sleep(LOOP_INTERVAL_SECONDS)

