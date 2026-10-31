#!/usr/bin/env python3
# runrnwnpxy.py
import os
import json
import sys
import time
import subprocess
import pytz
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama for clean, aligned dashboard terminal formatting
init(autoreset=True)

# 🔍 STRATEGIC FOOTPRINT: Dedicated data tracking state path
current_dir = os.path.dirname(os.path.abspath(__file__))
STATE_FILE_PATH = os.path.abspath(os.path.join(current_dir, "../../web/webrnwnstatepxy.json"))

# STRATEGIC FIXATION CONSTANTS
BRICK_SIZE = 140.0           # Fixed outperformance box step size
INITIAL_LOSS_FLOOR = -1400.0   # Symmetrical base absolute loss limit threshold
TRAILING_DROP_GAP = 1400.0   # Strict trailing trigger gap from peak milestone (Peak - 1400)

# ✅ RESET GUARD VERIFICATION TIMEOUTS
FLAT_CONFIRM_TIMEOUT_SECONDS = 10.0
FLAT_CONFIRM_POLL_SECONDS = 2.0

def _load_tracker_state():
    """Extracts internal operational metrics and rolling mid-day offsets from the state cache."""
    default_state = {
        "winners_peak_brick": 0.0, 
        "consecutive_breaches": 0, 
        "pnl_offset": 0.0,      
        "last_date": ""
    }
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

def broker_positions_flat():
    """Reset guard. Returns True ONLY when the broker itself confirms zero open positions."""
    try:
        from runclntpxy import get_session
        client = get_session()
        if not client:
            return False
            
        def _num(v): return float(str(v).replace(",", "").strip() or 0)
        
        deadline = time.time() + FLAT_CONFIRM_TIMEOUT_SECONDS
        while True:
            res = client.positions()
            if isinstance(res, dict):
                data = res.get("data")
                if isinstance(data, list):
                    is_flat = True
                    for pos in data:
                        net_qty = _num(pos.get("net_qty", 0))
                        if net_qty == 0:
                            net_qty = _num(pos.get("flBuyQty", 0)) - _num(pos.get("flSellQty", 0))
                        if abs(net_qty) > 0:
                            is_flat = False
                            break
                    if is_flat: return True
                elif "no data" in str(res.get("errMsg", "") or res.get("message", "")).lower():
                    return True
            if time.time() >= deadline:
                return False
            time.sleep(FLAT_CONFIRM_POLL_SECONDS)
    except Exception:
        return False

def calculate_runners_and_winners_pnl(open_df, closed_df):
    """
    Surgically aggregates PNL, checks triggers, flattens positions, and completely 
    re-initializes brackets inline so trading automatically restarts in the next loop.
    Enforces a calendar date check to block yesterday's stale state.
    """
    # 1. Standardize Data Structures safely to avoid runtime attribute crashes
    df_open = open_df.copy() if (open_df is not None and not open_df.empty) else pd.DataFrame(columns=["Buy_Prc", "Sell_Prc", "PNL"])
    df_closed = closed_df.copy() if (closed_df is not None and not closed_df.empty) else pd.DataFrame(columns=["Buy_Prc", "Sell_Prc", "PNL"])
    
    # 2. Strict Mathematical Winner Filtering Layers (Buy < Sell/LTP outperformance)
    win_open = df_open[df_open["Buy_Prc"] < df_open["Sell_Prc"]] if not df_open.empty else df_open
    win_closed = df_closed[df_closed["Buy_Prc"] < df_closed["Sell_Prc"]] if not df_closed.empty else df_closed
    
    raw_winners_pnl = float(win_open["PNL"].sum() + win_closed["PNL"].sum())
    raw_losers_pnl = float((df_open["PNL"].sum() + df_closed["PNL"].sum()) - raw_winners_pnl)
    
    # 3. Alignment Layout Rounding Engine: Force last digit to strictly lock to 0
    def force_zero_ending(val):
        return int(round(val / 10.0) * 10)

    fmt_losers = force_zero_ending(raw_losers_pnl)
    fmt_winners = force_zero_ending(raw_winners_pnl)
    
    # 4. Dynamic Rolling Cache State Initialization with Strict Date Filter
    ist_tz = pytz.timezone('Asia/Kolkata')
    today_str = datetime.now(ist_tz).strftime('%Y-%m-%d')
    
    state = _load_tracker_state()
    
    # 🛑 DAY-ROLLOVER GUARD: If the cached date doesn't match today, purge everything instantly
    if state["last_date"] != today_str:
        state["winners_peak_brick"] = 0.0
        state["consecutive_breaches"] = 0
        state["pnl_offset"] = 0.0

    winners_peak_brick = state["winners_peak_brick"]
    consecutive_breaches = state["consecutive_breaches"]
    pnl_offset = state["pnl_offset"]
    
    # Calculate live returns relative to the current fresh game instance
    total_raw_pnl = float(df_open["PNL"].sum() + df_closed["PNL"].sum())
    current_game_pnl = total_raw_pnl - pnl_offset
    
    # Lock the peak brick milestone strictly inside the active fresh start window
    if current_game_pnl > winners_peak_brick:
        completed_bricks = int(current_game_pnl // BRICK_SIZE)
        new_peak = float(completed_bricks * BRICK_SIZE)
        if new_peak > winners_peak_brick:
            winners_peak_brick = new_peak
            consecutive_breaches = 0

    # 5. PASSIVE AUTOMATED DUAL-RISK MATRIX EVALUATION
    is_breached = False
    
    # Condition A: Absolute -1400 Symmetrical Fresh Game Floor Check
    if current_game_pnl <= INITIAL_LOSS_FLOOR:
        is_breached = True
        
    # Condition B: Trailing Peak Floor logic (Symmetrical Peak - 1400 Trigger)
    elif winners_peak_brick > 0:
        active_trailing_exit = winners_peak_brick - TRAILING_DROP_GAP
        if current_game_pnl <= active_trailing_exit:
            is_breached = True

    # 6. DYNAMIC 40-CHARACTER RADAR TELEMETRY DISPLAY LAYER
    # Center text elements perfectly inside a 40-character dashboard column window
    line_border = "+" + "-" * 38 + "+"
    hdr_txt     = f"|{'— LIVE TELEMETRY RADAR —':^38}|"
    pnl_txt     = f"| Game PnL : {int(current_game_pnl):<6} | Peak : {int(winners_peak_brick):<6} |"
    mkt_txt     = f"| Losers   : {fmt_losers:<6} | Winners: {fmt_winners:<6} |"
    candle_txt  = f"|{'harjantalcandle':^38}|"
    
    # Render aligned console layouts
    print(f"\n{Fore.CYAN}{line_border}")
    print(f"{Fore.CYAN}{hdr_txt}")
    print(f"{Fore.CYAN}{line_border}")
    print(f"{Fore.WHITE}{pnl_txt}")
    print(f"{Fore.WHITE}{mkt_txt}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}{candle_txt}")
    print(f"{Fore.CYAN}{line_border}\n")

    # 7. One-Time Active Flattening and Instant Post-Reset Self-Healing Action
    if is_breached:
        consecutive_breaches += 1
        if consecutive_breaches >= 3:
            # 🚨 40-CHARACTER BREACH ALARM ROW
            sys.stdout.write(f"\n{Fore.RED}{Style.BRIGHT} !! CRITICAL TRADING BREACH DETECTED !! {Style.RESET_ALL}\n")
            sys.stdout.flush()
            
            print(f"🚨 {Fore.RED}Risk threshold hit! Dispatching emergency market cleanup routing...")
            
            # Shifted resolution targeting up one folder level into parent directory
            parent_dir = os.path.dirname(current_dir)
            script_path = os.path.join(parent_dir, "exesqrpxy.py")
            python_executable = sys.executable if sys.executable else "python"
            
            # Fire the standalone square-off tool from the parent path directory locations
            subprocess.run([python_executable, script_path, "-all"])
            
            # 🔄 AUTOMATED INLINE RESTART PIPELINE
            if broker_positions_flat():
                pnl_offset = total_raw_pnl  
                winners_peak_brick = 0.0    
                consecutive_breaches = 0    
    else:
        if consecutive_breaches > 0:
            consecutive_breaches = 0
            
    _save_tracker_state(winners_peak_brick, consecutive_breaches, pnl_offset, today_str)
    return fmt_losers, fmt_winners
