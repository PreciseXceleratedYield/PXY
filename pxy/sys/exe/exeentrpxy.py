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
DEBUG = False
COUNTERBUY = "NO"
COOL_DOWN_SECONDS = 300  # 5 Minutes per side
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

# --- HELPER FUNCTIONS (COOLING & RESET) ---
def reset_daily_cooling():
    """Clears cooling files at 9:15 AM IST for a fresh start."""
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    if now.hour == 9 and now.minute == 15:
        for side in ["ce", "pe"]:
            f = f"exebal_cool_{side}.txt"
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

def is_side_cooling(side):
    """Checks if a side is cooling and self-cleans expired files."""
    file_path = f"exebal_cool_{side.lower()}.txt"
    if not os.path.exists(file_path): return False
    try:
        with open(file_path, "r") as f:
            last_ts = float(f.read().strip())
        elapsed = time.time() - last_ts
        if elapsed < COOL_DOWN_SECONDS:
            return True
        os.remove(file_path)
        return False
    except: return False

def set_side_cooling(side):
    """Starts the 5-minute timer for a side."""
    with open(f"exebal_cool_{side.lower()}.txt", "w") as f:
        f.write(str(time.time()))

def dprint(msg, color=Fore.CYAN):
    if DEBUG: print(f"{Style.BRIGHT}{color}[DEBUG] {msg}{Style.RESET_ALL}")

# --- IMPORTS ---
try:
    from syspxy import get_all_data
    from runclntpxy import get_session
    from runfundpxy import get_available_funds
    from runpchkpxy import get_position_summary
    from runsymbpxy import get_symbol
except Exception as e:
    print(f"{Fore.RED}IMPORT ERROR: {e}"); sys.exit(1)

def execute_order(client, symbol, qty):
    try:
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": "B", "amo": "NO",
            "disclosed_quantity": "0", "market_protection": "0"
        }
        res = client.place_order(**params)
        return {"stat": "OK" if res and str(res).strip() else "FAIL", "raw": res}
    except Exception as e:
        return {"stat": "FAIL", "err": str(e)}

async def main():
    dprint("===== MAIN START =====", Fore.GREEN)
    try:
        reset_daily_cooling()
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()

        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 19) <= now < dt_time(15, 31)):
            print("⏳ Market buffer time - skipped")
            return

        client = get_session()
        if not client: return

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
        except:
            OTM_DISTANCE, is_bull, is_bear = 100, False, False

        exit_sig = str(reversal).upper().strip() if reversal else "NONE"
        if not entry_signal: return

        sig = entry_signal.upper().strip()
        if sig == "STBUY": sig = "ATMBUY"
        elif sig == "STSELL": sig = "ATMSELL"
        original_sig = sig

        # --- POSITION CHECK ---
        pos = get_position_summary(client)
        if isinstance(pos, (list, tuple, set, dict)):
            ce_active, pe_active = "1CE" in str(pos), "1PE" in str(pos)
        else:
            ce_active, pe_active = "1CE" in str(pos), "1PE" in str(pos)

        # --- REGIME CORRECTION ---
        if COUNTERBUY.upper() == "YES":
            if ce_active and pe_active: sig = "NONE"
            elif exit_sig in ["BUY", "BULL"]:
                if pe_active: sig = "ATMBUY" if is_bull else "OTMBUY"
            elif exit_sig in ["SELL", "BEAR"]:
                if ce_active: sig = "ATMSELL" if is_bear else "OTMSELL"

        # --- EXECUTION BRANCHES ---
        symbol, res = None, {"stat": "SKIPPED"}
        
        if sig in ["ATMBUY", "OTMBUY"]:
            if ce_active:
                print("CE already active → SKIP")
            elif not is_side_cooling("CE"):
                symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                if symbol and symbol != "NA":
                    res = execute_order(client, symbol, LOT_SIZE)
                    if res["stat"] == "OK": set_side_cooling("CE")

        elif sig in ["ATMSELL", "OTMSELL"]:
            if pe_active:
                print("PE already active → SKIP")
            elif not is_side_cooling("PE"):
                symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                if symbol and symbol != "NA":
                    res = execute_order(client, symbol, LOT_SIZE)
                    if res["stat"] == "OK": set_side_cooling("PE")

        funds = get_available_funds(client)
        print(f""" ===================================== 💰 Cash : {int(funds)} 📦 Pos : {pos} 🎫 Symbol : {symbol} 🎯 Signal : {entry_signal} 📌 Status : {res.get('stat')} ===================================== """)

    except Exception:
        print(traceback.format_exc() if DEBUG else "❌ Main error")

if __name__ == "__main__":
    asyncio.run(main())


