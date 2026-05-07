import sys
import asyncio
import os
import time
import pytz
import traceback
import re
from pathlib import Path
from datetime import datetime, time as dt_time
from colorama import Fore, init, Style

# --- GLOBAL CONFIG ---
DEBUG = True # Set to True for full surgical debug logs
COUNTERBUY = "NO"
COOL_DOWN_SECONDS = 300 # 5 Minutes per side
init(autoreset=True)

# --- PATH SETUP ---
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
RUN_DIR = HERE / "run"
for p in [HERE, RUN_DIR, PARENT]:
    if str(p) not in sys.path:
        sys.path.append(str(p))

from syscnfgpxy import TICKER

# --- LOT SIZE LOGIC ---
t = TICKER.upper().strip()
LOT_SIZE = 30 if t == "^NSEBANK" else 65 if t == "^NSEI" else None

# --- DEBUG PRINT ---
def dprint(msg, color=Fore.CYAN):
    if DEBUG:
        print(f"{Style.BRIGHT}{color}[DEBUG] {msg}{Style.RESET_ALL}")

# --- HELPER FUNCTIONS (COOLING & RESET) ---
def reset_daily_cooling():
    """Clears cooling files at 9:15 AM IST for a fresh start."""
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if now.hour == 9 and now.minute == 15:
        for side in ["ce", "pe"]:
            f = f"exebal_cool_{side}.txt"
            if os.path.exists(f):
                try: 
                    os.remove(f)
                    dprint(f"Daily Reset: Cleared {f}", Fore.YELLOW)
                except: pass

def is_side_cooling(side):
    """Checks if a side is cooling and self-cleans expired files."""
    file_path = f"exebal_cool_{side.lower()}.txt"
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r") as f:
            last_ts = float(f.read().strip())
        elapsed = time.time() - last_ts
        if elapsed < COOL_DOWN_SECONDS:
            dprint(f"{side} is COOLING. {int(COOL_DOWN_SECONDS - elapsed)}s left.", Fore.WHITE)
            return True
        os.remove(file_path)
        dprint(f"{side} cooling expired. File deleted.", Fore.CYAN)
        return False
    except:
        return False

def set_side_cooling(side):
    """Starts the 5-minute timer for a side."""
    with open(get_cooling_file(side) if 'get_cooling_file' in globals() else f"exebal_cool_{side.lower()}.txt", "w") as f:
        f.write(str(time.time()))
    dprint(f"Cooling SET for {side}.", Fore.YELLOW)

# --- IMPORTS ---
dprint("IMPORTING MODULES...")
try:
    from syspxy import get_all_data
    from runclntpxy import get_session
    from runfundpxy import get_available_funds
    from runpchkpxy import get_position_summary
    from runsymbpxy import get_symbol
    dprint("IMPORTS SUCCESS", Fore.GREEN)
except Exception as e:
    print(f"{Fore.RED}IMPORT ERROR: {e}"); sys.exit(1)

def execute_order(client, symbol, qty):
    dprint(f"ENTER execute_order for {symbol}")
    try:
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "MKT",
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": "B",
            "amo": "NO",
            "disclosed_quantity": "0",
            "market_protection": "0"
        }
        dprint(f"ORDER PARAMS: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        dprint(f"ORDER RESPONSE: {res}", Fore.GREEN)
        return {"stat": "OK" if res and str(res).strip() else "FAIL", "raw": res}
    except Exception as e:
        dprint(f"ORDER ERROR: {e}", Fore.RED)
        return {"stat": "FAIL", "err": str(e)}

async def main():
    dprint("===== MAIN START =====", Fore.GREEN)
    try:
        reset_daily_cooling()
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()
        dprint(f"TIME CHECK: {now}")

        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 19) <= now < dt_time(15, 31)):
            print("⏳ Market buffer time - skipped")
            return

        dprint("CREATING SESSION...")
        client = get_session()
        if not client: 
            dprint("SESSION FAILED", Fore.RED)
            return

        dprint("GETTING DATA FROM SYSPXY...")
        data = get_all_data()
        entry_signal = data.get("entry")
        reversal = data.get("exit")
        ltp = data.get("price")

        # --- DYNAMIC OTM & SUPERTREND ---
        try:
            TO, YC = int(float(data.get("TO"))), int(float(data.get("YC")))
            OTM_DISTANCE = (round(abs(TO - YC) / 100) * 100) * 2
            supertrend = str(data.get("supertrend", "")).upper().strip()
            is_bull, is_bear = (supertrend == "UP"), (supertrend == "DOWN")
            dprint(f"OTM DIST: {OTM_DISTANCE} | SUPERTREND: {supertrend}")
        except Exception as e:
            dprint(f"OTM fallback: {e}", Fore.YELLOW)
            OTM_DISTANCE, is_bull, is_bear = 100, False, False

        exit_sig = str(reversal).upper().strip() if reversal else "NONE"
        dprint(f"EXIT REGIME: {exit_sig}")

        if not entry_signal: 
            print("WAIT SIGNAL: None")
            return

        sig = entry_signal.upper().strip()
        if sig == "STBUY": sig = "ATMBUY"
        elif sig == "STSELL": sig = "ATMSELL"
        original_sig = sig
        dprint(f"NORMALIZED SIGNAL: {sig}")

        # --- POSITION CHECK ---
        dprint("CHECKING POSITIONS...")
        pos = get_position_summary(client)
        dprint(f"POS RAW: {pos}")
        ce_active, pe_active = "1CE" in str(pos), "1PE" in str(pos)
        dprint(f"CE_ACTIVE: {ce_active} | PE_ACTIVE: {pe_active}")

        # --- REGIME CORRECTION ---
        if COUNTERBUY.upper() == "YES":
            dprint("REGIME OVERRIDE START...", Fore.MAGENTA)
            if ce_active and pe_active: 
                sig = "NONE"
                dprint("Both Active -> NONE", Fore.RED)
            elif exit_sig in ["BUY", "BULL"]:
                if pe_active: 
                    sig = "ATMBUY" if is_bull else "OTMBUY"
                    dprint(f"Regime Bull -> Changed to {sig}", Fore.GREEN)
            elif exit_sig in ["SELL", "BEAR"]:
                if ce_active: 
                    sig = "ATMSELL" if is_bear else "OTMSELL"
                    dprint(f"Regime Bear -> Changed to {sig}", Fore.GREEN)

        # --- EXECUTION BRANCHES ---
        symbol, res = None, {"stat": "SKIPPED"}
        
        if sig in ["ATMBUY", "OTMBUY"]:
            dprint("BRANCH: BUY CE")
            if ce_active:
                print("CE already active → SKIP")
            elif not is_side_cooling("CE"):
                symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                dprint(f"FETCHED SYMBOL: {symbol}")
                if symbol and symbol != "NA":
                    res = execute_order(client, symbol, LOT_SIZE)
                    if res["stat"] == "OK": set_side_cooling("CE")
            else:
                dprint("CE SKIP due to cooling")

        elif sig in ["ATMSELL", "OTMSELL"]:
            dprint("BRANCH: BUY PE")
            if pe_active:
                print("PE already active → SKIP")
            elif not is_side_cooling("PE"):
                symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                dprint(f"FETCHED SYMBOL: {symbol}")
                if symbol and symbol != "NA":
                    res = execute_order(client, symbol, LOT_SIZE)
                    if res["stat"] == "OK": set_side_cooling("PE")
            else:
                dprint("PE SKIP due to cooling")

        dprint("FETCHING FUNDS FOR SUMMARY...")
        funds = get_available_funds(client)
        
        # --- DASHBOARD OUTPUT ---
        print(f"""
 =====================================
     💰 Cash   : {int(funds)}
     📦 Pos    : {pos}
     🎫 Symbol : {symbol}
     🎯 Signal : {entry_signal}
     📌 Status : {res.get('stat')}
 =====================================
        """)
        dprint("===== MAIN END =====", Fore.GREEN)

    except Exception:
        print(traceback.format_exc() if DEBUG else "❌ Main error")

if __name__ == "__main__":
    asyncio.run(main())



