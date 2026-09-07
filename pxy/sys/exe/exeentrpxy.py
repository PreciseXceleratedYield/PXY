import sys
import asyncio
import os
import time
import pytz
import traceback
import re
import json
from pathlib import Path
from datetime import datetime, time as dt_time
from colorama import Fore, init, Style
import subprocess
# --- GLOBAL CONFIG ---
DEBUG = True 
COUNTERBUY = "NO" 
COOL_DOWN_SECONDS = 35

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
    from execepepxy import get_target_quantities 
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
    print(f"{Fore.CYAN}🔍 [DEBUG] ENTER execute_order for {symbol} | Qty: {qty}")
    try:
        order_tag = generate_pxy_tag()
        
        # Safe flat baseline limit price for illiquid or un-traded OTM premium contracts
        # The exchange will automatically fill you at the best available lower seller price
        fallback_limit_price = 5.00 
        
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": f"{fallback_limit_price:.2f}", # Formatted string representation
            "order_type": "L",                     # Strictly 'L' or 'Limit' for Neo SDK
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": "B",
            "amo": "NO",
            "tag": order_tag
        }
        
        dprint(f"DISPATCHING LIMIT ORDER: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        print(f"{Fore.MAGENTA}📬 [DEBUG] RAW API RESPONSE: {res}")
        
        # Strict validation checks matching Kotak Neo architecture
        is_valid_success = False
        if isinstance(res, dict):
            stat_flag = str(res.get("stat", "")).upper()
            err_msg = str(res.get("errMsg", "")).lower()
            
            if (stat_flag == "OK" or res.get("stCode") == 0) and "rejected" not in err_msg:
                is_valid_success = True

        if is_valid_success:
            print(f"{Fore.GREEN}        🚀 SUCCESS -> {symbol} | {order_tag}")
            return {"stat": "OK", "raw": res}
        else:
            print(f"{Fore.RED}        ❌ FAILURE STATUS RETURNED -> {symbol} | {order_tag}")
            return {"stat": "FAIL", "raw": res}

    except Exception as e:
        print(f"{Fore.RED}💥 [DEBUG] CRITICAL EXCEPTION DURING API EXECUTION:")
        print(traceback.format_exc())
        return {"stat": "FAIL", "err": str(e)}


async def main():
    dprint("===== MAIN START =====", Fore.GREEN)
    try:
        reset_daily_cooling()
        IST = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(IST)
        now = now_ist.time()
        dprint(f"TIME CHECK: {now}")

        # 1. Check Market Timing First
        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 11) <= now < dt_time(15, 50)):
            print(f"{Fore.YELLOW}⏳ Market buffer time - skipped")
            return

        # --- 2. EARLY CE/PE POSITION CHECK ---
        # Fetching session early specifically to pull positions before running anything else
        client = get_session()
        if not client:
            return

        pos_raw = str(get_position_summary(client)).upper().strip() # Upstream format: "XCEYPE"
        match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
        if match:
            ce_lots = int(match.group(1))
            pe_lots = int(match.group(2))
        else:
            dprint(f"⚠️ Upstream position layout error: '{pos_raw}'. Using fallback 0.", Fore.YELLOW)
            ce_lots, pe_lots = 0, 0

        # CRITICAL RE-ROUTE GATE: If both sides have active positions, completely skip execution loop
        if ce_lots > 0 and pe_lots > 0:
            print(f"{Fore.YELLOW}I will handover to balance agent")
            return

        # 3. Fetch Data and Check Signal Status
        data = get_all_data()
        entry_signal = str(data.get("entry", "")).upper().strip()
        reversal = data.get("exit")

        if entry_signal in ["BULL", "BEAR", "NONE", "WAIT", ""]:
            print(f"{Fore.MAGENTA}🛑  NO-ACTION signal({entry_signal if entry_signal else 'BLANK'})- BUY skipped")
            return

        # Run script in the sub-directory
        subprocess.run([sys.executable, str(RUN_DIR / "runnftfutpxy.py")])

        # Read the price from the JSON file in the sub-directory
        with open(RUN_DIR / "nftfut.json", "r") as f:
            json_value = float(json.load(f).get("price"))

        # Fetch original LTP and calculate mathematical average
        ltp = (float(data.get("price")) + json_value) / 2

        try:
            supertrend_val = str(data.get("supertrend", "")).upper().strip()
            
            # --- DYNAMIC OTM DISTANCE BY DAY OF THE WEEK (IST) ---
            current_day = now_ist.strftime('%A')
            day_otm_mapping = {
                "Monday": 100,
                "Tuesday": 75,
                "Wednesday": 50,
                "Thursday": 25,
                "Friday": 0
            }
            base_otm_distance = day_otm_mapping.get(current_day, 100)
            
            # Time-based variable x (100 inside 9:15-9:30 IST, 0 otherwise)
            start_time = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
            end_time = now_ist.replace(hour=9, minute=30, second=0, microsecond=0)
            x = 100 if start_time <= now_ist <= end_time else 0
            
            OTM_DISTANCE = base_otm_distance + x
        except Exception: 
            supertrend_val = "NONE"
            OTM_DISTANCE = 100

        exit_sig = str(reversal).upper().strip() if reversal else "NONE"
        if not entry_signal: return

        sig = entry_signal.upper().strip()
        if sig == "STBUY": sig = "ATMBUY"
        elif sig == "STSELL": sig = "ATMSELL"
        dprint(f"SIGNAL: {sig}")
        
        # --- SURGICAL IMPORT RESTORATION FROM EXECEPEPXY ---
        try:
            from execepepxy import get_target_quantities
        except Exception as imp_err:
            print(f"{Fore.RED}CRITICAL: Failed to import get_target_quantities from execepepxy: {imp_err}")
            return

        dprint(f"CURRENT -> CE LOTS: {ce_lots} | PE LOTS: {pe_lots}")
        
        # Fetch target limits directly as clean lot counts
        max_allowed_ce_lots, max_allowed_pe_lots = get_target_quantities(supertrend_val, ce_lots, pe_lots, LOT_SIZE)
        dprint(f"SUPERTREND: {supertrend_val} | MAX CE LOTS: {max_allowed_ce_lots} | MAX PE LOTS: {max_allowed_pe_lots}")

        # --- INTERCEPTING DISTANCE OFFSET LOGIC FOR STRIKES ---
        if "ATM" in sig:
            current_distance = 0
        elif "OTM" in sig:
            current_distance = OTM_DISTANCE
        else:
            current_distance = 0

        dprint(f"ROUTING TO BUILDER -> SIGNAL: {sig} | DISTANCE ARGUMENT: {current_distance}")

        symbol, res = None, {"stat": "SKIPPED"}
        is_flat_bypass = (ce_lots == 0 and pe_lots == 0)

        if sig in ["ATMBUY", "OTMBUY"]:
            dprint("BRANCH: BALANCE CE")
            if is_flat_bypass or (ce_lots < max_allowed_ce_lots) or (ce_lots == 0 and pe_lots == 0 and max_allowed_ce_lots > 0):
                if not is_side_cooling("CE"):
                    symbol = get_symbol(ltp, sig, current_distance)
                    if symbol and symbol != "NA":
                        res = execute_order(client, symbol, LOT_SIZE)
                        if res["stat"] == "OK": set_side_cooling("CE")
            else:
                dprint(f"SKIP: CE Lots ({ce_lots}) hit or exceeded strategy limit ({max_allowed_ce_lots})", Fore.YELLOW)

        elif sig in ["ATMSELL", "OTMSELL"]:
            dprint("BRANCH: BALANCE PE")
            if is_flat_bypass or (pe_lots < max_allowed_pe_lots) or (ce_lots == 0 and pe_lots == 0 and max_allowed_pe_lots > 0):
                if not is_side_cooling("PE"):
                    symbol = get_symbol(ltp, sig, current_distance)
                    if symbol and symbol != "NA":
                        res = execute_order(client, symbol, LOT_SIZE)
                        if res["stat"] == "OK": set_side_cooling("PE")
            else:
                dprint(f"SKIP: PE Lots ({pe_lots}) hit or exceeded strategy limit ({max_allowed_pe_lots})", Fore.YELLOW)

        funds = get_available_funds(client)

        print(f"""
 ============ BUY ACTION =============
         🎯  Signal : {entry_signal}
         📈  Trend  : {supertrend_val}
         📦  Pos    : {pos_raw}
         📌  Status : {res.get('stat')}
 =====================================
 """)
        dprint("===== MAIN END =====", Fore.GREEN)
    except Exception:
        print(traceback.format_exc() if DEBUG else "❌ Main error")


if __name__ == "__main__":
    asyncio.run(main())
