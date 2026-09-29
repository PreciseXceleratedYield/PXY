#!/usr/bin/env python3
# exernkopxy.py (Part 1)
import os
import sys
import json
import time
import pytz
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# 🛡️ GLOBAL OPERATIONAL SWITCH CONFIGURATION
EXECUTE_SQUARE_OFF = False # 🛑 LIVE INTRADAY EXECUTION PERMANENTLY DEACTIVATED

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
CHECK_STATE_FILE = os.path.abspath(os.path.join(current_dir, "../../web/webrnkchkpxy.json"))

# RISK CONFIGURATION CONSTANTS
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
    except (json.JSONDecodeError, PermissionError):
        return None
    except Exception as e:
        print(f"{Fore.RED}⚠️ Critical Parse Error on {os.path.basename(file_path)}: {e}")
        return 0.0

def load_check_state():
    """Loads consecutive breach counter to maintain context across external supervisor loops."""
    if not os.path.exists(CHECK_STATE_FILE):
        return {"consecutive_breaches": 0}
    try:
        with open(CHECK_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"consecutive_breaches": 0}

def save_check_state(counter):
    """Saves consecutive breach status cleanly to disk."""
    try:
        payload = {
            "consecutive_breaches": int(counter),
            "updated_time": datetime.now().strftime('%H:%M:%S')
        }
        with open(CHECK_STATE_FILE, "w") as f:
            json.dump(payload, f, indent=4)
    except Exception:
        pass

def load_session_state():
    if not os.path.exists(RENKO_STATE_FILE):
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -float(TRAILING_DROP_LIMIT)}
    try:
        with open(RENKO_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -float(TRAILING_DROP_LIMIT)}

def save_session_state(peak_value, current_net, exit_line):
    try:
        os.makedirs(os.path.dirname(RENKO_STATE_FILE), exist_ok=True)
        
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
# exernkopxy.py (Part 2)

def verify_and_purge_stale_cache():
    """Instantly clears stale web files if their update dates don't match today's date."""
    IST = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")
    
    state = load_session_state()
    last_update_time = state.get("updated_timestamp", "")
    
    if today_str not in last_update_time:
        print(f"\n⏰ {Fore.GREEN}{Style.BRIGHT}NEW TRADING DAY DETECTED! RUNNING INSTANT DATA PURGE...")
        
        SQUAREOFF_LOG_FILE = os.path.abspath(os.path.join(current_dir, "../../web/websqrpxy.json"))
        for target_file_path in [PNL_JSON_PATH, POS_JSON_PATH, SQUAREOFF_LOG_FILE, CHECK_STATE_FILE]:
            if os.path.exists(target_file_path):
                file_mod_timestamp = os.path.getmtime(target_file_path)
                file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
                if file_mod_date_str != today_str:
                    print(f"⚠️ {Fore.YELLOW}STALE FILE DETECTED: {os.path.basename(target_file_path)} belongs to yesterday ({file_mod_date_str}).")
                    try:
                        with open(target_file_path, "w") as fw:
                            if "pxy.json" in target_file_path:
                                json.dump([], fw)
                            else:
                                json.dump({"consecutive_breaches": 0}, fw)
                        print(f"🧹 {Fore.GREEN}Successfully purged stale data from {os.path.basename(target_file_path)}.")
                    except Exception as file_err:
                        print(f"{Fore.RED}❌ Error clearing stale file: {file_err}")
                        
        save_session_state(0.0, 0.0, -float(TRAILING_DROP_LIMIT))
        save_check_state(0)
        print(f"🧹 {Fore.CYAN}Cleaned up tracking cache file: {RENKO_STATE_FILE}\n")


def start_trailing_engine():
    """Monitors live data boundaries on a pure read-only observation basis. No intraday resets or orders."""
    verify_and_purge_stale_cache()

    initial_state = load_session_state()
    session_peak_pnl = float(initial_state.get("session_peak_pnl", 0.0))
    
    check_state = load_check_state()
    consecutive_breaches = int(check_state.get("consecutive_breaches", 0))
    
    try:
        realised_pnl = safe_load_json_pnl(PNL_JSON_PATH)
        unrealised_pnl = safe_load_json_pnl(POS_JSON_PATH)
        
        if realised_pnl is None or unrealised_pnl is None:
            save_check_state(0)
            sys.exit(0)
            
        current_net_pnl = realised_pnl + unrealised_pnl
        
        # Shift peak upwards dynamically if cumulative returns hit new records
        if current_net_pnl > session_peak_pnl:
            session_peak_pnl = current_net_pnl
            
        float_drop_limit = float(TRAILING_DROP_LIMIT)
        active_exit_line = session_peak_pnl - float_drop_limit
        save_session_state(session_peak_pnl, current_net_pnl, active_exit_line)
        
        sign_prefix = "+" if active_exit_line > 0 else ""
        exit_display_str = "0.0k" if active_exit_line == 0 else f"{sign_prefix}{active_exit_line / 1000.0:.1f}k"
        
        net_color = Fore.GREEN if current_net_pnl >= 0 else Fore.RED
        
        print(
            f"Exit@{Fore.WHITE}{Style.BRIGHT}{exit_display_str}{Style.RESET_ALL} | "
            f"📊 Net:{net_color}₹{current_net_pnl:,.0f}{Style.RESET_ALL} | "
            f"Peak@{Fore.WHITE}₹{session_peak_pnl:,.0f}{Style.RESET_ALL}"
        )

        # -------- READ-ONLY MONITORING THRESHOLD MATRIX --------
        if current_net_pnl <= active_exit_line:
            consecutive_breaches += 1
            save_check_state(consecutive_breaches)
            
            if consecutive_breaches >= 3:
                # 🚨 CRITICAL ONE-LINE WARNING LAYER (Exactly 40 characters wide string)
                # Text length: "!! CRITICAL TRADING BREACH DETECTED !!" is exactly 38 chars + 2 flanking spaces = 40 chars
                sys.stdout.write(f"\n{Fore.RED}{Style.BRIGHT} !! CRITICAL TRADING BREACH DETECTED !! {Style.RESET_ALL}\n")
                sys.stdout.flush()
                sys.exit(0)
        else:
            if consecutive_breaches > 0:
                save_check_state(0)
            sys.exit(0)

    except Exception as e:
        print(f"{Fore.RED}Execution Error inside tracker engine: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_trailing_engine()
