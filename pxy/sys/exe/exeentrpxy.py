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
COOL_DOWN_SECONDS = 65
MAX_LOTS = 3  # ⚡ MAX RISK PROTECTION PARAMETER (Limits exposure to 3 lots max per side)

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
MAX_ALLOWED_QTY = (LOT_SIZE * MAX_LOTS) if LOT_SIZE else 0

# --- DEBUG PRINT ---
def dprint(msg, color=Fore.CYAN):
    if DEBUG:
        print(f"{Style.BRIGHT}{color}[DEBUG] {msg}{Style.RESET_ALL}")

# --- HELPER FUNCTIONS ---
def reset_daily_cooling():
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
    except: return False

def set_side_cooling(side):
    file_path = f"exebal_cool_{side.lower()}.txt"
    with open(file_path, "w") as f:
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

# --- Updated Tag Generator for Day Trading ---
def generate_pxy_tag():
    """Generates a pure timestamp tag: HHMMSS"""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).strftime('%H%M%S')

def execute_order(client, symbol, qty):
    dprint(f"ENTER execute_order for {symbol}")
    try:
        # Generate the unique ID for this specific scalp
        order_tag = generate_pxy_tag()
        
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
            "tag": order_tag  # Attaching the HHMMSS tag
        }
        
        dprint(f"ORDER PARAMS: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        
        # Log the tag with the response for verification
        print(f"{Fore.CYAN}🚀 ORDER PLACED | SYMBOL: {symbol} | TAG: {order_tag}")
        
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

        # 1. Check Market Timing First
        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 19) <= now < dt_time(15, 31)):
            print(f"{Fore.YELLOW}⏳ Market buffer time - skipped")
            return

        # 2. Fetch Data and Check Signal Status
        data = get_all_data()
        entry_signal = str(data.get("entry", "")).upper().strip()
        reversal = data.get("exit")

        if entry_signal in ["BULL", "BEAR", "NONE", "WAIT", ""]:
            print(f"{Fore.MAGENTA}🛑  NO-ACTION signal({entry_signal if entry_signal else 'BLANK'})- BUY skipped")
            return

        # --- SESSION INITIALIZATION (Only runs for actionable signals) ---
        client = get_session()
        if not client:
            return

        ltp = data.get("price")

        try:
            supertrend = str(data.get("supertrend", "")).upper().strip()
            OTM_DISTANCE = 200
        except: OTM_DISTANCE = 100

        exit_sig = str(reversal).upper().strip() if reversal else "NONE"
        if not entry_signal: return

        sig = entry_signal.upper().strip()
        if sig == "STBUY": sig = "ATMBUY"
        elif sig == "STSELL": sig = "ATMSELL"
        dprint(f"SIGNAL: {sig}")

        # --- UPDATED POSITION BALANCING LOGIC (+1 SUPERTREND CUSHION & ATM/OTM) ---
        dprint("CHECKING POSITION STATE FOR 1:1 WITH +1 BIAS...")
        pos_raw = str(get_position_summary(client))
        
        # Safe extraction of quantities
        ce_qty = int(re.search(r'(\d+)CE', pos_raw).group(1)) if 'CE' in pos_raw else 0
        pe_qty = int(re.search(r'(\d+)PE', pos_raw).group(1)) if 'PE' in pos_raw else 0
        
        dprint(f"CURRENT -> CE: {ce_qty} | PE: {pe_qty} | SUPERTREND: {supertrend} | SIGNAL: {sig}")

        symbol, res = None, {"stat": "SKIPPED"}
        
        if supertrend == "BULL":
            # Enforce CE must be exactly 1 lot higher than PE
            if ce_qty < (pe_qty + LOT_SIZE):
                # Hard restriction ceiling check
                if ce_qty < MAX_ALLOWED_QTY:
                    if not is_side_cooling("CE"):
                        # Dynamically uses your ATMBUY or OTMBUY entry signals
                        symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                        if symbol and symbol != "NA":
                            res = execute_order(client, symbol, LOT_SIZE)
                            if res["stat"] == "OK": set_side_cooling("CE")
                else:
                    dprint(f"CRITICAL OVERRIDE: CE position ({ce_qty}) is at MAX CAP ({MAX_ALLOWED_QTY}). Order blocked.", Fore.RED)
            else:
                dprint(f"SKIP: CE({ce_qty}) already has the +1 lot advantage over PE({pe_qty})", Fore.YELLOW)

        elif supertrend == "BEAR":
            # Enforce PE must be exactly 1 lot higher than CE
            if pe_qty < (ce_qty + LOT_SIZE):
                # Hard restriction ceiling check
                if pe_qty < MAX_ALLOWED_QTY:
                    if not is_side_cooling("PE"):
                        # Dynamically uses your ATMSELL or OTMSELL entry signals
                        symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                        if symbol and symbol != "NA":
                            res = execute_order(client, symbol, LOT_SIZE)
                            if res["stat"] == "OK": set_side_cooling("PE")
                else:
                    dprint(f"CRITICAL OVERRIDE: PE position ({pe_qty}) is at MAX CAP ({MAX_ALLOWED_QTY}). Order blocked.", Fore.RED)
            else:
                dprint(f"SKIP: PE({pe_qty}) already has the +1 lot advantage over CE({ce_qty})", Fore.YELLOW)
        
        else:
            dprint(f"SKIP: Unknown Supertrend state: {supertrend}", Fore.RED)

        funds = get_available_funds(client)

        print(f"""
 =====================================
         💰  Cash   : {int(funds)}
         📦  Pos    : {pos_raw}
         🎫  Symbol : {symbol}
         🎯  Signal : {entry_signal}
         📌  Status : {res.get('stat')}
 =====================================
 """)
        dprint("===== MAIN END =====", Fore.GREEN)
    except Exception:
        print(traceback.format_exc() if DEBUG else "❌ Main error")

if __name__ == "__main__":
    asyncio.run(main())

