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
from pathlib import Path
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output alignment
init(autoreset=True)

# 🔍 STRATEGIC FOOTPRINT: Path isolation handling matching your execution structure
current_dir = os.path.dirname(os.path.abspath(__file__)) # This is pxy/sys/exe/
run_dir = os.path.join(current_dir, "run")

# Inject subfolder paths to system paths so python resolves your runlilopxy imports cleanly
if current_dir not in sys.path:
    sys.path.append(current_dir)
if run_dir not in sys.path:
    sys.path.append(run_dir)

# 🎯 USER-INDEPENDENT WORKSPACE PATH RESOLUTION
HOME_DIR = str(Path.home())

PNL_JSON_PATH = os.path.abspath(os.path.join(HOME_DIR, "pxy/web/webpnlpxy.json"))
POS_JSON_PATH = os.path.abspath(os.path.join(HOME_DIR, "pxy/web/webpospxy.json"))
RENKO_STATE_FILE = os.path.abspath(os.path.join(HOME_DIR, "pxy/web/webrinkopxy.json"))
CHECK_STATE_FILE = os.path.abspath(os.path.join(HOME_DIR, "pxy/web/webrnkchkpxy.json"))

# STRATEGIC FIXATION CONSTANTS
BRICK_SIZE = 140.0           # Fixed outperformance box step size
INITIAL_LOSS_FLOOR = -1400.0   # Symmetrical base absolute loss limit threshold
TRAILING_DROP_GAP = 1400.0   # Strict trailing trigger gap from peak milestone (Peak - 1400)

# ✅ RESET GUARD VERIFICATION TIMEOUTS
FLAT_CONFIRM_TIMEOUT_SECONDS = 10.0
FLAT_CONFIRM_POLL_SECONDS = 2.0

def load_check_state():
    """Loads consecutive breach counter safely from disk."""
    if not os.path.exists(CHECK_STATE_FILE):
        return {"consecutive_breaches": 0}
    try:
        with open(CHECK_STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # If the file is locked or half-written, raise to retry; don't wipe counters!
        raise

def save_check_state(counter):
    """Saves consecutive breach status cleanly using an ATOMIC OS REPLACE write operation."""
    try:
        payload = {
            "consecutive_breaches": int(counter),
            "updated_time": datetime.now().strftime('%H:%M:%S')
        }
        tmp_file = CHECK_STATE_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(payload, f, indent=4)
        os.replace(tmp_file, CHECK_STATE_FILE) # 🔒 ATOMIC: Zero chance of mid-write reading corruption
    except Exception as e:
        print(f"⚠️ Error atomizing check state write loop: {e}")

def load_session_state():
    """Loads session state parameters cleanly. Distinguishes missing files from corruption blocks."""
    if not os.path.exists(RENKO_STATE_FILE):
        return None # 🆕 Returning None guarantees a clean morning initialization sequence
    try:
        with open(RENKO_STATE_FILE, "r") as f:
            d = json.load(f)
            return {
                "session_peak_pnl": float(d.get("session_peak_pnl", 0.0)),
                "current_net_pnl": float(d.get("current_net_pnl", 0.0)),
                "active_exit_line": float(d.get("active_exit_line", -1400.0)),
                "pnl_offset": float(d.get("pnl_offset", 0.0)),
                "updated_timestamp": d.get("updated_timestamp", "") # 🎯 FIXED: Timestamp returned!
            }
    except Exception:
        raise # 🔒 CRITICAL: Raise the error to force a loop skip instead of wiping your values!

def save_session_state(peak_value, current_net, exit_line, pnl_offset_val):
    """Writes values back atomizing files to prevent dashboard cross-reading collisions."""
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
        tmp_file = RENKO_STATE_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(payload, f, indent=4)
        os.replace(tmp_file, RENKO_STATE_FILE) # 🔒 ATOMIC: Replaces file instantly in one single frame step
    except Exception as e:
        print(f"{Fore.RED}⚠️ Downstream Web State Sync Error: {e}")

def verify_and_purge_stale_cache(state_on_disk):
    """Surgically clears previous day data EXACTLY ONCE daily on date transition shifts."""
    IST = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")
    
    # Resolve the timestamp out of the disk state payload safely
    last_update_time = state_on_disk.get("updated_timestamp", "") if state_on_disk else ""
    
    # 🎯 PURGE ONCE DAILY DETECTED CONFLICT FILTER WINDOW
    if today_str not in last_update_time:
        print(f"\n⏰ {Fore.GREEN}{Style.BRIGHT}NEW DAY DETECTED! RUNNING INTRA-DAY WEB JSON CACHE PURGE...")
        
        SQUAREOFF_LOG_FILE = os.path.abspath(os.path.join(HOME_DIR, "pxy/web/websqrpxy.json"))
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
    from run.runclntpxy import get_session
    from run import runlilopxy  
    
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Failed to establish broker session client.")
        return

    # 1️⃣ DATA-GUARD FENCE: Protects memory parameters from post-market empty dataframes
    open_df, closed_df = runlilopxy.process_lilo_orders(client)
    if (open_df is None or open_df.empty) and (closed_df is None or closed_df.empty):
        print(f"ℹ️ {Fore.YELLOW}No active market data found. Retaining current web cache parameters...")
        return

    # 2️⃣ ATOMIC READ GATEWAY: Try reading disk state context safely. Skip tick if locked.
    try:
        state_on_disk = load_session_state()
        check_state_on_disk = load_check_state()
    except Exception as read_err:
        print(f"⚠️ {Fore.YELLOW}File lock or read collision frame encountered: {read_err}. Skipping this tick frame...")
        return

    # 3️⃣ PURGE CONFLICT SEQUENCE TIMING: Executes exactly once daily before tracking high extraction passes
    verify_and_purge_stale_cache(state_on_disk)

    # 4️⃣ STATE PARSING LAYER: Initialize metrics or treat missing file context as clean morning slate
    if state_on_disk is None:
        historical_peak_record = 0.0
        pnl_offset = 0.0
        consecutive_breaches = 0
    else:
        historical_peak_record = float(state_on_disk.get("session_peak_pnl", 0.0))
        pnl_offset = float(state_on_disk.get("pnl_offset", 0.0))
        consecutive_breaches = int(check_state_on_disk.get("consecutive_breaches", 0))

    df_open = open_df.copy()
    df_closed = closed_df.copy()

    # Force normalize all column headers to strictly uppercase to prevent any __getitem__ crashes
    df_open.columns = [str(c).upper() for c in df_open.columns]
    df_closed.columns = [str(c).upper() for c in df_closed.columns]

    # Structural re-indexing cushion filling missing structural keys with 0.0 baseline indicators
    for df_target in [df_open, df_closed]:
        for req_col in ["BUY_PRC", "SELL_PRC", "PNL"]:
            if req_col not in df_target.columns:
                df_target[req_col] = 0.0

    # 2. Strict Mathematical Winner Filtering Layers (Case-armored)
    win_open = df_open[df_open["BUY_PRC"] < df_open["SELL_PRC"]] if not df_open.empty else df_open
    win_closed = df_closed[df_closed["BUY_PRC"] < df_closed["SELL_PRC"]] if not df_closed.empty else df_closed
    
    raw_winners_pnl = float(win_open["PNL"].sum() + win_closed["PNL"].sum())
    raw_losers_pnl = float((df_open["PNL"].sum() + df_closed["PNL"].sum()) - raw_winners_pnl)
    
    def force_zero_ending(val):
        return int(round(val / 10.0) * 10)

    fmt_losers = force_zero_ending(raw_losers_pnl)
    fmt_winners = force_zero_ending(raw_winners_pnl)
    
    # 3. Process Game Progress Mathematics relative to active offsets
    total_raw_pnl = float(df_open["PNL"].sum() + df_closed["PNL"].sum())
    current_game_pnl = total_raw_pnl - pnl_offset
    
    # 📈 CALCULATE LIVE BRICKS FOR THIS TICK ONLY
    completed_bricks = int(current_game_pnl // BRICK_SIZE)
    calculated_live_peak = float(completed_bricks * BRICK_SIZE)
    
    # 🔒 UNBREAKABLE TRACKING MATRIX LAYER
    # Core mathematical high-water mark protection comparison filter.
    # Evaluates live tick values against record peak values extracted from disk memory,
    # making a peak variable reduction completely impossible when live PnL drops.
    winners_peak_brick = max(calculated_live_peak, historical_peak_record)

    # 📊 DYNAMIC EXIT RECALCULATION: Anchored purely to your permanently frozen peak
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
            
    # Sync final values securely back to disk cache file systems using atomic replace routines
    save_session_state(winners_peak_brick, current_game_pnl, active_trailing_exit, pnl_offset)

if __name__ == "__main__":
    pipe_master_execution_ledger()
