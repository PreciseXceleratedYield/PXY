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

# =====================================================================
# 📋 PART 1: GLOBAL CONFIGURATIONS & DEFINITIONS
# =====================================================================

# 🛡️ GLOBAL OPERATIONAL SWITCH CONFIGURATION
EXECUTE_SQUARE_OFF = True  # LIVE PROTECTION ACTIVATED

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

# RISK CONFIGURATION CONSTANTS (DYNAMIC TRAILING PARAMETERS)
INITIAL_LOSS_FLOOR = -9000.0
DYNAMIC_RISK_BAND = 9000.0  # Distance maintained behind the day's peak profit
EMERGENCY_RETRY_SECONDS = 5.0
LOOP_INTERVAL_SECONDS = 1.0


def safe_load_realised_pnl(file_path):
    """Safely extracts cumulative REALISED metrics from webpnlpxy.json."""
    if not os.path.exists(file_path):
        return 0.0
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(IST)
        today_str = now_ist.strftime("%Y-%m-%d")
        
        if os.path.getsize(file_path) == 0:
            return 0.0
            
        file_mod_timestamp = os.path.getmtime(file_path)
        file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
        
        if file_mod_date_str != today_str:
            sys.stdout.write(f"\r⚠️  {Fore.YELLOW}STALE REALISED DATA BLOCKED...{Style.RESET_ALL}\n")
            sys.stdout.flush()
            return 0.0

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: 
                return 0.0
            data = json.loads(content)
            total_realised = 0.0
            rows = data if isinstance(data, list) else [data]
            for row in rows:
                if not isinstance(row, dict): 
                    continue
                pnl_val = row.get("PNL") if row.get("PNL") is not None else row.get("pnl")
                if pnl_val is not None:
                    try:
                        total_realised += float(pnl_val)
                    except (ValueError, TypeError):
                        continue
            return total_realised
    except Exception as e:
        print(f"{Fore.RED}⚠ Realised Parse Error: {e}")
        return 0.0


def safe_load_unrealised_pnl(file_path):
    """Safely extracts cumulative UNREALISED metrics from webpospxy.json."""
    if not os.path.exists(file_path):
        return 0.0
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(IST)
        today_str = now_ist.strftime("%Y-%m-%d")
        
        if os.path.getsize(file_path) == 0:
            return 0.0
            
        file_mod_timestamp = os.path.getmtime(file_path)
        file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
        
        if file_mod_date_str != today_str:
            sys.stdout.write(f"\r⚠️  {Fore.YELLOW}STALE UNREALISED DATA BLOCKED...{Style.RESET_ALL}\n")
            sys.stdout.flush()
            return 0.0

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: 
                return 0.0
            data = json.loads(content)
            total_unrealised = 0.0
            rows = data if isinstance(data, list) else [data]
            
            valid_keys = {"UNREALIZED", "UNREALISED", "M2M", "UR_PNL", "URPNL"}
            for row in rows:
                if not isinstance(row, dict): 
                    continue
                upper_row = {str(k).upper(): v for k, v in row.items() if v is not None}
                for key in valid_keys:
                    if key in upper_row:
                        try:
                            total_unrealised += float(upper_row[key])
                            break
                        except (ValueError, TypeError):
                            continue
            return total_unrealised
    except Exception as e:
        print(f"{Fore.RED}⚠ Unrealised Parse Error: {e}")
        return 0.0


def calculate_dynamic_profit_target(file_path):
    """Counts active rows indiscriminately and updates the target using a 1400 per-row metric."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return 0.0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: 
                return 0.0
            data = json.loads(content)
            active_rows_count = 0
            rows = data if isinstance(data, list) else [data]
            for row in rows:
                if not isinstance(row, dict): 
                    continue
                
                raw_qty = row.get("QTY") or row.get("Qty") or row.get("qty") or 0.0
                try:
                    quantity = abs(float(raw_qty))
                except (ValueError, TypeError):
                    quantity = 0.0
                    
                # Guard against partial residue lots or micro decimal positions
                if quantity > 0.1:
                    active_rows_count += 1
                        
            if active_rows_count == 0: 
                return 0.0
            return float(active_rows_count * 1400.0)
    except Exception:
        return 0.0


def load_session_state():
    """Retrieves session parameter states safely."""
    fallback_state = {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": INITIAL_LOSS_FLOOR}
    if not os.path.exists(RENKO_STATE_FILE) or os.path.getsize(RENKO_STATE_FILE) == 0:
        return fallback_state
    try:
        with open(RENKO_STATE_FILE, "r", encoding="utf-8") as f: 
            return json.load(f)
    except Exception:
        return fallback_state


def save_session_state(peak_value, current_net, exit_line):
    """Saves session parameters securely to the local state file."""
    try:
        os.makedirs(os.path.dirname(RENKO_STATE_FILE), exist_ok=True)
        payload = {
            "session_peak_pnl": float(peak_value), 
            "current_net_pnl": float(current_net),
            "active_exit_line": float(exit_line), 
            "updated_timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(RENKO_STATE_FILE, "w", encoding="utf-8") as f: 
            json.dump(payload, f, indent=4)
    except Exception as e:
        print(f"{Fore.RED}⚠ State Sync Error: {e}")


def verify_and_purge_stale_cache():
    """Instantly clears stale web files if dates don't match today's date."""
    IST = pytz.timezone("Asia/Kolkata")
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    state = load_session_state()
    
    if today_str not in state.get("updated_timestamp", ""):
        print(f"\n⏰ {Fore.GREEN}NEW TRADING DAY! PURGING STALE FILES...")
        for path in [PNL_JSON_PATH, POS_JSON_PATH, SQUAREOFF_LOG_FILE]:
            if os.path.exists(path):
                try:
                    f_mod = datetime.fromtimestamp(os.path.getmtime(path), IST).strftime("%Y-%m-%d")
                    if f_mod != today_str:
                        with open(path, "w", encoding="utf-8") as fw: 
                            json.dump([], fw)
                except Exception: 
                    pass
        save_session_state(0.0, 0.0, INITIAL_LOSS_FLOOR)


def write_squareoff_success_log():
    """Generates a tracking timestamp payload confirming completely cleared positions."""
    try:
        os.makedirs(os.path.dirname(SQUAREOFF_LOG_FILE), exist_ok=True)
        now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
        payload = {
            "status": "SUCCESS", 
            "action": "SQUARE_OFF_ALL_POSITIONS",
            "timestamp_ist": now_ist.strftime('%Y-%m-%d %H:%M:%S'), 
            "unix_timestamp": time.time()
        }
        with open(SQUAREOFF_LOG_FILE, "w", encoding="utf-8") as f: 
            json.dump(payload, f, indent=4)
        print(f"📝 {Fore.GREEN}Square-off log updated successfully at {payload['timestamp_ist']} IST.")
    except Exception as e:
        print(f"{Fore.RED}⚠ Failed to write log: {e}")
# =====================================================================
# 📈 PART 2: CALCULATION & CORE LOGIC ENGINE
# =====================================================================

def start_trailing_engine():
    """Monitors live data boundaries continuously.
    Implements a dynamic -9000 floor trailing method linked directly to daily peak profits.
    """
    verify_and_purge_stale_cache()
    
    # Load past session state to handle mid-day core engine restarts safely
    initial_state = load_session_state()
    session_peak_pnl = float(initial_state.get("session_peak_pnl", 0.0))
    
    # Calculate baseline trailing exit line parameter
    active_exit_line = session_peak_pnl - DYNAMIC_RISK_BAND
    if active_exit_line < INITIAL_LOSS_FLOOR:
        active_exit_line = INITIAL_LOSS_FLOOR

    print(f"\n🚀 {Fore.CYAN}STARTING DYNAMIC TRAILING RUNTIME ENGINE... [INITIAL FLOOR @ -₹9,000]{Style.RESET_ALL}\n")
    
    while True:
        try:
            # 1. Gather live operational data metrics from web files
            realised_pnl = safe_load_realised_pnl(PNL_JSON_PATH)    # Booked PnL
            unrealised_pnl = safe_load_unrealised_pnl(POS_JSON_PATH) # Running PnL
            current_net_pnl = realised_pnl + unrealised_pnl         # Total Net PnL
            profit_target = calculate_dynamic_profit_target(POS_JSON_PATH)
            
            # 2. Dynamic Trailing Core Update Step Rule logic
            if current_net_pnl > session_peak_pnl:
                session_peak_pnl = current_net_pnl
                # Reduce risk footprint dynamically by shifting the floor up with the peak
                active_exit_line = session_peak_pnl - DYNAMIC_RISK_BAND
            
            # Ensure the tracking floor never sinks beneath our absolute start day cap
            if active_exit_line < INITIAL_LOSS_FLOOR:
                active_exit_line = INITIAL_LOSS_FLOOR
            
            # 3. Persist current operational states for the monitoring dashboard
            save_session_state(session_peak_pnl, current_net_pnl, active_exit_line)
            
            # 4. Format terminal logging display strings
            target_display_str = "OFF (No Rows)" if profit_target == 0.0 else f"+₹{profit_target:,.0f}"
            pnl_color = Fore.GREEN if current_net_pnl >= 0 else Fore.RED
            floor_color = Fore.YELLOW if active_exit_line > INITIAL_LOSS_FLOOR else Fore.RED
            
            # Single-line terminal carriage return ticker
            sys.stdout.write(
                f"\r📉 Floor:{floor_color}₹{active_exit_line:,.0f}{Style.RESET_ALL} | "
                f"🎯 Target:{Fore.CYAN}{target_display_str}{Style.RESET_ALL} | "
                f"📈 Peak: {Fore.GREEN}₹{session_peak_pnl:,.0f}{Style.RESET_ALL} | "
                f"📊 Net PnL:{pnl_color}₹{current_net_pnl:,.0f}{Style.RESET_ALL}      "
            )
            sys.stdout.flush()

            # =====================================================================
            # 🛡️ EVALUATION & BREACH DETECTION TIMELINE
            # =====================================================================
            
            # Condition A: Dynamic Take Profit Target Evaluation (Checked against Total NET PnL)
            if profit_target > 0.0 and current_net_pnl >= profit_target:
                if EXECUTE_SQUARE_OFF:
                    print(f"\n\n🎯 {Fore.GREEN}PROFIT TARGET HIT! Triggering exit routine...{Style.RESET_ALL}")
                    execute_emergency_sequence(current_dir, session_peak_pnl, current_net_pnl, active_exit_line)
                else:
                    print(f"\n\n⚠️ {Fore.YELLOW}PROFIT TARGET HIT but EXECUTE_SQUARE_OFF is disabled.{Style.RESET_ALL}")
                    sys.exit(0)

            # Condition B: Dynamic Trailing Floor Evaluation (Checked against Total NET PnL)
            elif current_net_pnl <= active_exit_line:
                if EXECUTE_SQUARE_OFF:
                    print(f"\n\n🚨 {Fore.RED}NET PNL BREACHED TRAILING FLOOR (₹{active_exit_line:,.0f})! Entering exit loop...{Style.RESET_ALL}")
                    execute_emergency_sequence(current_dir, session_peak_pnl, current_net_pnl, active_exit_line)
                else:
                    print(f"\n\n⚠️ {Fore.YELLOW}WARNING: Trailing floor violated. Protection disabled.{Style.RESET_ALL}")
                    sys.exit(0)
            
            # Heartbeat check cadence interval
            time.sleep(LOOP_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            print(f"\n\n👋 {Fore.YELLOW}Engine monitoring terminated manually by user.{Style.RESET_ALL}")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Fore.RED}❌ Execution Error inside tracker loop: {e}{Style.RESET_ALL}")
            time.sleep(EMERGENCY_RETRY_SECONDS)


def execute_emergency_sequence(current_dir, final_peak, final_net, final_floor):
    """Encapsulated execution framework to clear orders and confirm empty account positions."""
    script_path = os.path.join(current_dir, "exesqrpxy.py")
    python_executable = sys.executable if sys.executable else "python"
    no_active_positions_counter = 0
    missing_script_attempts = 0
    
    while True:
        print(f"⚡ [{time.strftime('%H:%M:%S')}] Firing: {python_executable} exesqrpxy.py -all")
        
        if os.path.exists(script_path):
            try:
                process = subprocess.Popen(
                    [python_executable, script_path, "-all"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
                )
                
                found_phrase_in_this_run = False
                
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    if "No active positions to exit" in line:
                        found_phrase_in_this_run = True
                
                try:
                    process.wait(timeout=15.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    print(f"{Fore.RED}❌ Square-off subprocess timed out and was killed forcibly.{Style.RESET_ALL}")
                    found_phrase_in_this_run = False
                
                if found_phrase_in_this_run:
                    no_active_positions_counter += 1
                    print(f"🎯 Grep Match! Confirmation Count: ({no_active_positions_counter}/3)")
                else:
                    no_active_positions_counter = 0  
                    
                if no_active_positions_counter >= 3:
                    print(f"\n✅ {Fore.GREEN}TRIPLE MATCH CONFIRMED: No open operational positions remain.{Style.RESET_ALL}")
                    write_squareoff_success_log()
                    save_session_state(final_peak, final_net, final_floor)
                    sys.exit(0)
                    
            except Exception as proc_err:
                print(f"{Fore.RED}❌ Subprocess execution framework routing error: {proc_err}{Style.RESET_ALL}")
                no_active_positions_counter = 0
        else:
            print(f"{Fore.RED}❌ Critical error: Square-off script missing at {script_path}{Style.RESET_ALL}")
            missing_script_attempts += 1
            if missing_script_attempts >= 3:
                print(f"🚨 {Fore.RED}FATAL: Core dependency unavailable. Manual fallback required!{Style.RESET_ALL}")
                sys.exit(1)
        
        print(f"⏳ Retry block pass done. Re-verifying in {EMERGENCY_RETRY_SECONDS} seconds...\n")
        time.sleep(EMERGENCY_RETRY_SECONDS)
# =====================================================================
# 🚀 PART 3: MAIN EXECUTION ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    start_trailing_engine()
