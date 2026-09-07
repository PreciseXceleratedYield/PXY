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
    dprint(f"ENTER execute_order for {symbol}")
    try:
        # Generate the unique ID for this specific scalp
        order_tag = generate_pxy_tag()
        
        # FIXED: Using a safe nominal Limit price ceiling with type "L" 
        # to ensure an immediate match while bypassing exchange 'LTP not available' rejections
        fallback_limit_price = 5.00
        
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": f"{fallback_limit_price:.2f}",
            "order_type": "L",  # Strictly 'L' or 'Limit' for Kotak Neo SDK validation
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": "B",
            "amo": "NO",
            "tag": order_tag
        }
        
        dprint(f"ORDER PARAMS: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        
        # Log the tag with the response for verification
        print(f"{Fore.CYAN}        🚀 {symbol} | {order_tag}")
        print(f"{Fore.MAGENTA}📬 [DEBUG] RAW API RESPONSE: {res}")
        
        # Strict validation checks matching Kotak Neo response payload patterns
        is_valid_success = False
        if isinstance(res, dict):
            stat_flag = str(res.get("stat", "")).upper()
            err_msg = str(res.get("errMsg", "")).lower()
            if (stat_flag == "OK" or res.get("stCode") == 0) and "rejected" not in err_msg:
                is_valid_success = True
        
        return {"stat": "OK" if is_valid_success else "FAIL", "raw": res}
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
        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15,11) <= now < dt_time(15, 50)):
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

        # Core anchor spot calculation price for downstream processing
        spot_reference_price = float(data.get("price", 0))

        try:
            supertrend_val = str(data.get("supertrend", "")).upper().strip()
            OTM_DISTANCE = 100
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

        # --- UPDATED POSITION BALANCING LOGIC (LOT BASED) ---
        dprint("CHECKING POSITIONS FOR BALANCE...")
        pos_raw = str(get_position_summary(client)).upper().strip() # Upstream format: "XCEYPE"
        
        # Hard-anchored regex to match your upstream format exactly
        match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
        if match:
            ce_lots = int(match.group(1))
            pe_lots = int(match.group(2))
        else:
            dprint(f"⚠️ Upstream position layout error: '{pos_raw}'. Using fallback 0.", Fore.YELLOW)
            ce_lots, pe_lots = 0, 0
        
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
                    # Step A: Generate the option target contract code name first using spot data
                    symbol = get_symbol(spot_reference_price, sig, current_distance)
                    if symbol and symbol != "NA":
                        # Step B: Run the generic token-LTP subprocess using the derived option contract name
                        print(f"{Fore.CYAN}🔍 Querying live data registry for option: {symbol}...")
                        subprocess.run([sys.executable, str(RUN_DIR / "runtknltppxy.py"), symbol])
                        
                        # Step C: Read back premium context updates from the single output file
                        with open(RUN_DIR / "nftfut.json", "r") as f:
                            ltp = float(json.load(f).get("price", 0))
                        print(f"{Fore.GREEN}🎯 Premium option target context resolved: {ltp:.2f}")
                        
                        # Place execution order
                        res = execute_order(client, symbol, LOT_SIZE)
                        if res["stat"] == "OK": set_side_cooling("CE")
            else:
                dprint(f"SKIP: CE Lots ({ce_lots}) hit or exceeded strategy limit ({max_allowed_ce_lots})", Fore.YELLOW)

        elif sig in ["ATMSELL", "OTMSELL"]:
            dprint("BRANCH: BALANCE PE")
            if is_flat_bypass or (pe_lots < max_allowed_pe_lots) or (ce_lots == 0 and pe_lots == 0 and max_allowed_pe_lots > 0):
                if not is_side_cooling("PE"):
                    # Step A: Generate the option target contract code name first using spot data
                    symbol = get_symbol(spot_reference_price, sig, current_distance)
                    if symbol and symbol != "NA":
                        # Step B: Run the generic token-LTP subprocess using the derived option contract name
                        print(f"{Fore.CYAN}🔍 Querying live data registry for option: {symbol}...")
                        subprocess.run([sys.executable, str(RUN_DIR / "runtknltppxy.py"), symbol])
                        
                        # Step C: Read back premium context updates from the single output file
                        with open(RUN_DIR / "nftfut.json", "r") as f:
                            ltp = float(json.load(f).get("price", 0))
                        print(f"{Fore.GREEN}🎯 Premium option target context resolved: {ltp:.2f}")
                        
                        # Place execution order
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
