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

# RISK CONFIGURATION CONSTANTS (HARD-CODED ABSOLUTE LOSS FLOOR)
HARD_LOSS_FLOOR = -9999.0
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
        file_mod_timestamp = os.path.getmtime(file_path)
        file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
        
        if file_mod_date_str != today_str:
            sys.stdout.write(f"\r⚠️  {Fore.YELLOW}STALE REALISED DATA BLOCKED...{Style.RESET_ALL}\n")
            sys.stdout.flush()
            return 0.0

        with open(file_path, "r") as f:
            content = f.read().strip()
            if not content: return 0.0
            data = json.loads(content)
            total_realised = 0.0
            rows = data if isinstance(data, list) else [data]
            for row in rows:
                if not isinstance(row, dict): continue
                if "PNL" in row and row["PNL"] is not None:
                    total_realised += float(row["PNL"])
                elif "pnl" in row and row["pnl"] is not None:
                    total_realised += float(row["pnl"])
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
        file_mod_timestamp = os.path.getmtime(file_path)
        file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
        
        if file_mod_date_str != today_str:
            sys.stdout.write(f"\r⚠️  {Fore.YELLOW}STALE UNREALISED DATA BLOCKED...{Style.RESET_ALL}\n")
            sys.stdout.flush()
            return 0.0

        with open(file_path, "r") as f:
            content = f.read().strip()
            if not content: return 0.0
            data = json.loads(content)
            total_unrealised = 0.0
            rows = data if isinstance(data, list) else [data]
            for row in rows:
                if not isinstance(row, dict): continue
                upper_row = {str(k).upper(): v for k, v in row.items() if v is not None}
                for key in ("UNREALIZED", "UNREALISED", "M2M", "UR_PNL", "URPNL"):
                    if key in upper_row:
                        total_unrealised += float(upper_row[key])
                        break
            return total_unrealised
    except Exception as e:
        print(f"{Fore.RED}⚠ Unrealised Parse Error: {e}")
        return 0.0


def calculate_dynamic_profit_target(file_path):
    """Counts active CE/PE legs. Returns 0.0 if positions are single-sided."""
    if not os.path.exists(file_path):
        return 0.0
    try:
        with open(file_path, "r") as f:
            content = f.read().strip()
            if not content: return 0.0
            data = json.loads(content)
            ce_count, pe_count = 0, 0
            rows = data if isinstance(data, list) else [data]
            for row in rows:
                if not isinstance(row, dict): continue
                symbol = str(row.get("SYMBOL") or row.get("Symbol") or row.get("symbol") or "").upper()
                quantity = abs(float(row.get("QTY") or row.get("Qty") or row.get("qty") or 0.0))
                if quantity > 0:
                    if "CE" in symbol: ce_count += 1
                    elif "PE" in symbol: pe_count += 1
            if ce_count == 0 or pe_count == 0: return 0.0
            return float((ce_count + pe_count) * 1500.0)
    except Exception:
        return 0.0


def load_session_state():
    if not os.path.exists(RENKO_STATE_FILE):
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": HARD_LOSS_FLOOR}
    try:
        with open(RENKO_STATE_FILE, "r") as f: return json.load(f)
    except Exception:
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": HARD_LOSS_FLOOR}


def save_session_state(peak_value, current_net, exit_line):
    try:
        os.makedirs(os.path.dirname(RENKO_STATE_FILE), exist_ok=True)
        payload = {
            "session_peak_pnl": float(peak_value), "current_net_pnl": float(current_net),
            "active_exit_line": float(exit_line), "updated_timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(RENKO_STATE_FILE, "w") as f: json.dump(payload, f, indent=4)
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
                f_mod = datetime.fromtimestamp(os.path.getmtime(path), IST).strftime("%Y-%m-%d")
                if f_mod != today_str:
                    try:
                        with open(path, "w") as fw: json.dump([], fw)
                    except Exception: pass
        save_session_state(0.0, 0.0, HARD_LOSS_FLOOR)


def write_squareoff_success_log():
    """Generates a tracking timestamp payload confirming completely cleared positions."""
    try:
        os.makedirs(os.path.dirname(SQUAREOFF_LOG_FILE), exist_ok=True)
        now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
        payload = {
            "status": "SUCCESS", "action": "SQUARE_OFF_ALL_POSITIONS",
            "timestamp_ist": now_ist.strftime('%Y-%m-%d %H:%M:%S'), "unix_timestamp": time.time()
        }
        with open(SQUAREOFF_LOG_FILE, "w") as f: json.dump(payload, f, indent=4)
        print(f"📝 {Fore.GREEN}Square-off log updated successfully at {payload['timestamp_ist']} IST.")
    except Exception as e:
        print(f"{Fore.RED}⚠ Failed to write log: {e}")
# =====================================================================
# 📈 PART 2: CALCULATION & CORE LOGIC ENGINE
# =====================================================================

def start_trailing_engine():
    """Monitors live data boundaries continuously.
    Uses a hard-coded absolute loss floor of -9999.
    """
    verify_and_purge_stale_cache()
    
    # HARD-CODED ABSOLUTE LOSS FLOOR BOUNDARY
    active_exit_line = HARD_LOSS_FLOOR
    
    print(f"\n🚀 {Fore.CYAN}STARTING RUNTIME ENGINE... [HARD-CODED FLOOR ACTIVE @ -₹9,999]{Style.RESET_ALL}\n")
    
    while True:
        try:
            # 1. Gather live operational data metrics from web files
            realised_pnl = safe_load_realised_pnl(PNL_JSON_PATH)    # Booked PnL
            unrealised_pnl = safe_load_unrealised_pnl(POS_JSON_PATH) # Running PnL
            current_net_pnl = realised_pnl + unrealised_pnl         # Total Net PnL
            profit_target = calculate_dynamic_profit_target(POS_JSON_PATH)
            
            # 2. Persist current operational states for the monitoring dashboard
            save_session_state(0.0, current_net_pnl, active_exit_line)
            
            # 3. Format terminal logging display strings
            target_display_str = "OFF (Single Side)" if profit_target == 0.0 else f"+₹{profit_target:,.0f}"
            pnl_color = Fore.GREEN if current_net_pnl >= 0 else Fore.RED
            
            # Single-line terminal carriage return ticker
            sys.stdout.write(
                f"\rFloor:{Fore.RED}₹-9,999{Style.RESET_ALL} | "
                f"🎯 Target:{Fore.CYAN}{target_display_str}{Style.RESET_ALL} | "
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
                    execute_emergency_sequence(current_dir)
                else:
                    print(f"\n\n⚠️ {Fore.YELLOW}PROFIT TARGET HIT but EXECUTE_SQUARE_OFF is disabled.{Style.RESET_ALL}")
                    sys.exit(0)

            # Condition B: Absolute Fixed Floor Evaluation (Checked against Total NET PnL)
            elif current_net_pnl <= active_exit_line:
                if EXECUTE_SQUARE_OFF:
                    print(f"\n\n🚨 {Fore.RED}NET PNL BREACHED FIXED -9,999 FLOOR! Entering exit loop...{Style.RESET_ALL}")
                    execute_emergency_sequence(current_dir)
                else:
                    print(f"\n\n⚠️ {Fore.YELLOW}WARNING: Net PnL floor (-₹9,999) violated. Protection disabled.{Style.RESET_ALL}")
                    sys.exit(0)
            
            # Heartbeat check cadence interval
            time.sleep(LOOP_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            print(f"\n\n👋 {Fore.YELLOW}Engine monitoring terminated manually by user.{Style.RESET_ALL}")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Fore.RED}❌ Execution Error inside tracker loop: {e}{Style.RESET_ALL}")
            time.sleep(EMERGENCY_RETRY_SECONDS)


def execute_emergency_sequence(current_dir):
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
                for line in process.stdout:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    if "No active positions to exit" in line:
                        found_phrase_in_this_run = True
                process.wait()
                
                if found_phrase_in_this_run:
                    no_active_positions_counter += 1
                    print(f"🎯 Grep Match! Confirmation Count: ({no_active_positions_counter}/3)")
                else:
                    no_active_positions_counter = 0  
                    
                if no_active_positions_counter >= 3:
                    print(f"\n✅ {Fore.GREEN}TRIPLE MATCH CONFIRMED: No open operational positions remain.{Style.RESET_ALL}")
                    write_squareoff_success_log()
                    save_session_state(0.0, 0.0, HARD_LOSS_FLOOR)
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
