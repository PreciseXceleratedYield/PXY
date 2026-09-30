#!/usr/bin/env python3
# exeexacpxy.py (Part 1)
import os
import json
import sys
import time
import subprocess
import pytz
import pandas as pd
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output alignment
init(autoreset=True)

# 🔍 STRATEGIC FOOTPRINT: Path isolation handling matching your execution structure
current_dir = os.path.dirname(os.path.abspath(__file__)) # This is pxy/sys/exe/
run_dir = os.path.join(current_dir, "run")

# Inject paths to system paths so python locates local companion imports smoothly
if current_dir not in sys.path:
    sys.path.append(current_dir)
if run_dir not in sys.path:
    sys.path.append(run_dir)

# 🎯 DEEP PATH RESOLUTION MAPPING: Climbs up 3 levels from pxy/sys/exe/ straight into pxy/web/

# 🎯 FULLY ALIGNED PATHS: Pointing exactly to your active lowercase environment
PNL_JSON_PATH = "/home/pxy/pxy/web/webpnlpxy.json"
POS_JSON_PATH = "/home/pxy/pxy/web/webpospxy.json"
RENKO_STATE_FILE = "/home/pxy/pxy/web/webrinkopxy.json"
CHECK_STATE_FILE = "/home/pxy/pxy/web/webrnkchkpxy.json"


# STRATEGIC FIXATION CONSTANTS
BRICK_SIZE = 140.0           # Fixed outperformance box step size
INITIAL_LOSS_FLOOR = -1400.0   # Symmetrical base absolute loss limit threshold
TRAILING_DROP_GAP = 1400.0   # Strict trailing trigger gap from peak milestone (Peak - 1400)

# ✅ RESET GUARD VERIFICATION TIMEOUTS
FLAT_CONFIRM_TIMEOUT_SECONDS = 10.0
FLAT_CONFIRM_POLL_SECONDS = 2.0

def load_check_state():
    """Loads consecutive breach counter from the legacy downstream schema file."""
    if not os.path.exists(CHECK_STATE_FILE):
        return {"consecutive_breaches": 0}
    try:
        with open(CHECK_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"consecutive_breaches": 0}

def save_check_state(counter):
    """Saves consecutive breach status cleanly using your downstream schema layout."""
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
    """Loads session state parameters cleanly matching your downstream web JSON schemas."""
    default_state = {"session_peak_pnl": 0.0, "current_net_pnl": 0.0, "active_exit_line": -1400.0, "pnl_offset": 0.0}
    if not os.path.exists(RENKO_STATE_FILE):
        return default_state
    try:
        with open(RENKO_STATE_FILE, "r") as f:
            d = json.load(f)
            return {
                "session_peak_pnl": float(d.get("session_peak_pnl", 0.0)),
                "current_net_pnl": float(d.get("current_net_pnl", 0.0)),
                "active_exit_line": float(d.get("active_exit_line", -1400.0)),
                "pnl_offset": float(d.get("pnl_offset", 0.0))
            }
    except Exception:
        return default_state

def save_session_state(peak_value, current_net, exit_line, pnl_offset_val):
    """Writes values back using exact legacy keys to keep downstream charts intact."""
    try:
        os.makedirs(os.path.dirname(RENKO_STATE_FILE), exist_ok=True)
        ist_tz = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist_tz)
        
        payload = {
            "session_peak_pnl": float(peak_value),
            "current_net_pnl": float(current_net),
            "active_exit_line": float(exit_line),
            "pnl_offset": float(pnl_offset_val),  
            "updated_timestamp": now_ist.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(RENKO_STATE_FILE, "w") as f:
            json.dump(payload, f, indent=4)
    except Exception as e:
        print(f"{Fore.RED}⚠️ Downstream Web State Sync Error: {e}")

def verify_and_purge_stale_cache():
    """Instant daily cache purges executing seamlessly on morning date transition markers."""
    IST = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")
    
    state = load_session_state()
    last_update_time = state.get("updated_timestamp", "")
    
    if today_str not in last_update_time:
        print(f"\n⏰ {Fore.GREEN}{Style.BRIGHT}NEW DAY DETECTED! RUNNING INTRA-DAY WEB JSON CACHE PURGE...")
        
        SQUAREOFF_LOG_FILE = os.path.abspath(os.path.join(current_dir, "../../../web/websqrpxy.json"))
        for target_file_path in [PNL_JSON_PATH, POS_JSON_PATH, SQUAREOFF_LOG_FILE, CHECK_STATE_FILE]:
            if os.path.exists(target_file_path):
                file_mod_timestamp = os.path.getmtime(target_file_path)
                file_mod_date_str = datetime.fromtimestamp(file_mod_timestamp, IST).strftime("%Y-%m-%d")
                if file_mod_date_str != today_str:
                    try:
                        with open(target_file_path, "w") as fw:
                            if "pxy.json" in target_file_path:
                                json.dump([], fw)
                            else:
                                json.dump({"consecutive_breaches": 0}, fw)
                    except Exception:
                        pass
                        
        save_session_state(0.0, 0.0, -1400.0, 0.0)
        save_check_state(0)
        print(f"🧹 {Fore.CYAN}Successfully synchronized cache state date boundaries.\n")

def broker_positions_flat(client):
    """Querying open legs directly from the broker session to protect active game transitions."""
    try:
        def _num(v): return float(str(v).replace(",", "").strip() or 0)
        res = client.positions()
        if isinstance(res, dict):
            data = res.get("data")
            if isinstance(data, list):
                for pos in data:
                    net_qty = _num(pos.get("net_qty", 0))
                    if net_qty == 0:
                        net_qty = _num(pos.get("flBuyQty", 0)) - _num(pos.get("flSellQty", 0))
                    if abs(net_qty) > 0: return False
                return True
            elif "no data" in str(res.get("errMsg", "") or res.get("message", "")).lower():
                return True
        return False
    except Exception:
        return False


# exeexacpxy.py (Part 2)

def pipe_master_execution_ledger():
    """Performs passes through LILO arrays, trailing peak bricks inside memory arrays."""
    # 🎯 Takeover daily purges cleanly on script execution startup
    verify_and_purge_stale_cache()

    from run.runclntpxy import get_session
    from run import runlilopxy  
    
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Failed to establish broker session client.")
        return

    # Load baseline state metrics securely from your unified json cache
    state = load_session_state()
    winners_peak_brick = float(state.get("session_peak_pnl", 0.0))
    pnl_offset = float(state.get("pnl_offset", 0.0))
    
    check_state = load_check_state()
    consecutive_breaches = int(check_state.get("consecutive_breaches", 0))

    # 1. Pull transaction frames straight from your original runlilopxy file 
    open_df, closed_df = runlilopxy.process_lilo_orders(client)
    
    df_open = open_df.copy() if (open_df is not None and not open_df.empty) else pd.DataFrame(columns=["Buy_Prc", "Sell_Prc", "PNL"])
    df_closed = closed_df.copy() if (closed_df is not None and not closed_df.empty) else pd.DataFrame(columns=["Buy_Prc", "Sell_Prc", "PNL"])
    
    # 2. Strict Mathematical Winner Filtering Layers
    win_open = df_open[df_open["Buy_Prc"] < df_open["Sell_Prc"]] if not df_open.empty else df_open
    win_closed = df_closed[df_closed["Buy_Prc"] < df_closed["Sell_Prc"]] if not df_closed.empty else df_closed
    
    raw_winners_pnl = float(win_open["PNL"].sum() + win_closed["PNL"].sum())
    raw_losers_pnl = float((df_open["PNL"].sum() + df_closed["PNL"].sum()) - raw_winners_pnl)
    
    def force_zero_ending(val):
        return int(round(val / 10.0) * 10)

    fmt_losers = force_zero_ending(raw_losers_pnl)
    fmt_winners = force_zero_ending(raw_winners_pnl)
    
    # 3. Process Game Progress Mathematics relative to active offsets
    total_raw_pnl = float(df_open["PNL"].sum() + df_closed["PNL"].sum())
    current_game_pnl = total_raw_pnl - pnl_offset
    
    # 📈 DYNAMIC HEIGHT LOCK: Peak bricks stack dynamically upward in solid multiples of 140
    if current_game_pnl > winners_peak_brick:
        completed_bricks = int(current_game_pnl // BRICK_SIZE)
        new_peak = float(completed_bricks * BRICK_SIZE)
        if new_peak > winners_peak_brick:
            winners_peak_brick = new_peak
            consecutive_breaches = 0

    # 📊 DYNAMIC EXIT RECALCULATION: Shifts up dynamically matching your max peak bricks
    active_trailing_exit = winners_peak_brick - TRAILING_DROP_GAP
    
    is_breached = False
    if current_game_pnl <= INITIAL_LOSS_FLOOR:
        is_breached = True
    elif winners_peak_brick > 0:
        if current_game_pnl <= active_trailing_exit:
            is_breached = True

    # 4. DYNAMIC 40-CHARACTER RADAR TELEMETRY DISPLAY LAYER
    line_border = "+" + "-" * 38 + "+"
    hdr_txt     = f"|{'— LIVE TELEMETRY RADAR —':^38}|"
    pnl_txt     = f"| Game PnL : {int(current_game_pnl):<6} | Peak : {int(winners_peak_brick):<6} |"
    mkt_txt     = f"| Losers   : {fmt_losers:<6} | Winners: {fmt_winners:<6} |"
    candle_txt  = f"|{'harjantalcandle':^38}|"
    
    print(f"\n{Fore.CYAN}{line_border}")
    print(f"{Fore.CYAN}{hdr_txt}")
    print(f"{Fore.CYAN}{line_border}")
    print(f"{Fore.WHITE}{pnl_txt}")
    print(f"{Fore.WHITE}{mkt_txt}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}{candle_txt}")
    print(f"{Fore.CYAN}{line_border}\n")

    # 5. One-Time Active Symmetrical Flattening Action Mechanics
    if is_breached:
        consecutive_breaches += 1
        save_check_state(consecutive_breaches)
        save_session_state(winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset)
        
        if consecutive_breaches >= 3:
            sys.stdout.write(f"\n{Fore.RED}{Style.BRIGHT} !! CRITICAL TRADING BREACH DETECTED !! {Style.RESET_ALL}\n")
            sys.stdout.flush()
            
            # Since this script runs inside sys/exe/, exesqrpxy.py is located right next to it in the same directory
            script_path = os.path.join(current_dir, "exesqrpxy.py")
            python_executable = sys.executable if sys.executable else "python"
            subprocess.run([python_executable, script_path, "-all"])
            
            # 🔄 AUTOMATED SELF-HEALING RESTART MATRIX
            if broker_positions_flat(client):
                print(f"🧹 {Fore.GREEN}Broker flat verified! Locking offset at ₹{total_raw_pnl:,.0f} and restarting engine...")
                pnl_offset = total_raw_pnl  
                winners_peak_brick = 0.0    
                consecutive_breaches = 0    
                active_trailing_exit = -1400.0
                save_check_state(0)
    else:
        if consecutive_breaches > 0:
            consecutive_breaches = 0
            save_check_state(0)
            
    # Sync final values to clear legacy default fallbacks permanently
    save_session_state(winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset)

if __name__ == "__main__":
    pipe_master_execution_ledger()

