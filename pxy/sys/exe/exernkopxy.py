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

# RISK CONFIGURATION CONSTANTS
TRAILING_DROP_LIMIT = 9000.0
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
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -TRAILING_DROP_LIMIT}
    try:
        with open(RENKO_STATE_FILE, "r") as f: return json.load(f)
    except Exception:
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -TRAILING_DROP_LIMIT}


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
        save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)


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
    """Monitors live data boundaries and executes targeted output grepping when limits are hit."""
    verify_and_purge_stale_cache()
    initial_state = load_session_state()
    session_peak_pnl = float(initial_state.get("session_peak_pnl", 0.0))
    
    try:
        realised_pnl = safe_load_realised_pnl(PNL_JSON_PATH)
        unrealised_pnl = safe_load_unrealised_pnl(POS_JSON_PATH)
        current_net_pnl = realised_pnl + unrealised_pnl
        profit_target = calculate_dynamic_profit_target(POS_JSON_PATH)
        
        if current_net_pnl > session_peak_pnl:
            session_peak_pnl = current_net_pnl
            
        active_exit_line = session_peak_pnl - TRAILING_DROP_LIMIT
        save_session_state(session_peak_pnl, current_net_pnl, active_exit_line)
        
        sign_prefix = "+" if active_exit_line > 0 else ""
        exit_display_str = "0.0k" if active_exit_line == 0 else f"{sign_prefix}{active_exit_line / 1000.0:.1f}k"
        target_display_str = "OFF (Single Side)" if profit_target == 0.0 else f"+₹{profit_target:,.0f}"
        
        print(f"Exit@{Fore.RED}₹{Style.BRIGHT}{exit_display_str}{Style.RESET_ALL} | 🎯 Target:{Fore.CYAN}{target_display_str}{Style.RESET_ALL}")
        print(f"📊 Net:{Fore.GREEN}₹{current_net_pnl:,.0f}{Style.RESET_ALL} | Peak@{Fore.YELLOW}₹{session_peak_pnl:,.0f}{Style.RESET_ALL}")

        # -------- TRIGGER AND BREAK LOGIC TIMELINE --------
        
        # 1. Take Profit Target Evaluation
        if profit_target > 0.0 and current_net_pnl >= profit_target:
            if EXECUTE_SQUARE_OFF:
                print(f"\n🚨 {Fore.GREEN}PROFIT TARGET HIT! Entering verification loop...")
                current_net_pnl = active_exit_line 
            else:
                print(f"\n⚠️  PROFIT TARGET HIT but execution disabled."); sys.exit(0)

        # 2. Trailing Stop Loss Evaluation
        if current_net_pnl <= active_exit_line:
            if EXECUTE_SQUARE_OFF:
                print(f"\n🚨 {Fore.RED}LOSS TRIGGER BREACHED! Entering loop...")
                script_path = os.path.join(current_dir, "exesqrpxy.py")
                python_executable = sys.executable if sys.executable else "python"
                no_active_positions_counter = 0
                
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
                                sys.stdout.write(line); sys.stdout.flush()
                                if "No active positions to exit" in line:
                                    found_phrase_in_this_run = True
                            process.wait()
                            
                            if found_phrase_in_this_run:
                                no_active_positions_counter += 1
                                print(f"🎯 Grep Match! Count: ({no_active_positions_counter}/3)")
                            else:
                                no_active_positions_counter = 0  
                                
                            if no_active_positions_counter >= 3:
                                print(f"\n✅ TRIPLE MATCH CONFIRMED: No positions remain active.")
                                write_squareoff_success_log()
                                save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                                sys.exit(0)
                        except Exception as proc_err:
                            print(f"{Fore.RED}❌ Process routing engine error: {proc_err}")
                            no_active_positions_counter = 0
                    else:
                        print(f"{Fore.RED}❌ Square-off script missing at: {script_path}")
                    
                    save_session_state(0.0, 0.0, -TRAILING_DROP_LIMIT)
                    print(f"⏳ Retry pass complete. Re-checking in {EMERGENCY_RETRY_SECONDS} seconds...\n")
                    time.sleep(EMERGENCY_RETRY_SECONDS)
            else:
                print(f"\n⚠️  WARNING TARGET BREACHED: {exit_display_str} violated!"); sys.exit(0)
        else:
            sys.exit(0)
    except Exception as e:
        print(f"{Fore.RED}Execution Error inside tracker engine: {e}"); sys.exit(1)


if __name__ == "__main__":
    start_trailing_engine()
