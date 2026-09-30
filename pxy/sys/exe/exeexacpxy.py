#!/usr/bin/env python3
# exeexacpxy.py
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

# 🔍 STRATEGIC FOOTPRINT: Explicit path isolation handling for parent directory structure
current_dir = os.path.dirname(os.path.abspath(__file__))
run_dir = os.path.join(current_dir, "run")

# Inject paths to system arrays so python locates local companion imports smoothly
if current_dir not in sys.path:
    sys.path.append(current_dir)
if run_dir not in sys.path:
    sys.path.append(run_dir)

# Dedicated web data tracking state path
STATE_FILE_PATH = os.path.abspath(os.path.join(current_dir, "web/webrnwnstatepxy.json"))

# STRATEGIC FIXATION CONSTANTS
BRICK_SIZE = 140.0           # Fixed outperformance box step size
INITIAL_LOSS_FLOOR = -1400.0   # Symmetrical base absolute loss limit threshold
TRAILING_DROP_GAP = 1400.0   # Strict trailing trigger gap from peak milestone (Peak - 1400)

# ✅ RESET GUARD VERIFICATION TIMEOUTS
FLAT_CONFIRM_TIMEOUT_SECONDS = 10.0
FLAT_CONFIRM_POLL_SECONDS = 2.0

def _load_tracker_state():
    """Extracts internal operational metrics and rolling mid-day offsets from the state cache."""
    default_state = {"winners_peak_brick": 0.0, "consecutive_breaches": 0, "pnl_offset": 0.0, "last_date": ""}
    if not os.path.exists(STATE_FILE_PATH):
        return default_state
    try:
        with open(STATE_FILE_PATH, "r") as f:
            d = json.load(f)
            return {
                "winners_peak_brick": float(d.get("winners_peak_brick", 0.0)),
                "consecutive_breaches": int(d.get("consecutive_breaches", 0)),
                "pnl_offset": float(d.get("pnl_offset", 0.0)),
                "last_date": str(d.get("last_date", ""))
            }
    except Exception:
        return default_state

def _save_tracker_state(peak_brick, breach_count, pnl_offset, today_str):
    """Saves updated metric states cleanly back to disk cache."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
        payload = {
            "winners_peak_brick": float(peak_brick),
            "consecutive_breaches": int(breach_count),
            "pnl_offset": float(pnl_offset),
            "last_date": str(today_str),
            "updated_time": datetime.now().strftime('%H:%M:%S')
        }
        with open(STATE_FILE_PATH, "w") as f:
            json.dump(payload, f, indent=4)
    except Exception:
        pass

def broker_positions_flat(client):
    """Reset guard verification loop querying live open legs directly from the broker session."""
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

def pipe_master_execution_ledger():
    """Main execution loop routing data processing through original lilo variables."""
    # 🔄 DIRECTORY MAPPING: Imports session handler from run folder and targets runlilopxy
    from run.runclntpxy import get_session
    from run import runlilopxy  
    
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Failed to establish broker session client.")
        return

    # Dynamic Rolling Cache State Initialization with Strict Date Filter
    ist_tz = pytz.timezone('Asia/Kolkata')
    today_str = datetime.now(ist_tz).strftime('%Y-%m-%d')
    
    state = _load_tracker_state()
    if state["last_date"] != today_str:
        state["winners_peak_brick"] = 0.0
        state["consecutive_breaches"] = 0
        state["pnl_offset"] = 0.0

    winners_peak_brick = state["winners_peak_brick"]
    consecutive_breaches = state["consecutive_breaches"]
    pnl_offset = state["pnl_offset"]

    # 1. Execute untouched original process function to grab live DataFrames from runlilopxy
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
    
    # 3. Process Game Progress Mathematics
    total_raw_pnl = float(df_open["PNL"].sum() + df_closed["PNL"].sum())
    current_game_pnl = total_raw_pnl - pnl_offset
    
    if current_game_pnl > winners_peak_brick:
        completed_bricks = int(current_game_pnl // BRICK_SIZE)
        new_peak = float(completed_bricks * BRICK_SIZE)
        if new_peak > winners_peak_brick:
            winners_peak_brick = new_peak
            consecutive_breaches = 0

    is_breached = False
    if current_game_pnl <= INITIAL_LOSS_FLOOR:
        is_breached = True
    elif winners_peak_brick > 0:
        active_trailing_exit = winners_peak_brick - TRAILING_DROP_GAP
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
        if consecutive_breaches >= 3:
            sys.stdout.write(f"\n{Fore.RED}{Style.BRIGHT} !! CRITICAL TRADING BREACH DETECTED !! {Style.RESET_ALL}\n")
            sys.stdout.flush()
            
            # Since this file sits in the root parent directory, it maps directly to exesqrpxy.py in the same folder level
            script_path = os.path.join(current_dir, "exesqrpxy.py")
            python_executable = sys.executable if sys.executable else "python"
            subprocess.run([python_executable, script_path, "-all"])
            
            if broker_positions_flat(client):
                pnl_offset = total_raw_pnl  
                winners_peak_brick = 0.0    
                consecutive_breaches = 0    
    else:
        if consecutive_breaches > 0:
            consecutive_breaches = 0
            
    _save_tracker_state(winners_peak_brick, consecutive_breaches, pnl_offset, today_str)

if __name__ == "__main__":
    pipe_master_execution_ledger()
