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
DEBUG = True 
COUNTERBUY = "NO" 
COOL_DOWN_SECONDS = 65
MAX_LOTS_PER_SIDE = 3  # ⚡ STRICT CAP: Maximum 3 Lots per side (Nifty: 195 qty, BankNifty: 90 qty)

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
            "tag": order_tag 
        }
        
        dprint(f"ORDER PARAMS: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        
        print(f"{Fore.CYAN}🚀 ORDER PLACED | SYMBOL: {symbol} | TAG: {order_tag}")
        return {"stat": "OK" if res and str(res).strip() else "FAIL", "raw": res}
    except Exception as e:
        dprint(f"ORDER ERROR: {e}", Fore.RED)
        return {"stat": "FAIL", "err": str(e)}

import ast  # Ensure this import is added at the top of your script

def parse_net_quantity(pos_raw, option_type):
    """
    Surgically extracts held net quantity from position data.
    Evaluates structures cleanly to prevent string match collision bugs.
    """
    opt = option_type.upper()
    total_qty = 0
    
    # 1. Attempt safe literal parsing of the raw string structure
    try:
        data = ast.literal_eval(pos_raw)
    except Exception:
        # Fallback regex targeting only metric structures if evaluating fails
        patterns = [
            r'(?:netqty|quantity|qty)[\s"\'::-]+([+-]?\d+)(?:.+?' + opt.lower() + r'|)',
            r'([+-]?\d+)\s*(?:qty|lots|slots)?\s*(?:of)?\s*[\w\d]+' + opt.lower()
        ]
        for pattern in patterns:
            match = re.search(pattern, pos_raw.lower())
            if match:
                try: 
                    return abs(int(match.group(1)))
                except ValueError: 
                    continue
        return 0

    # 2. Extract positions safely depending on object shell type
    positions = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    
    # 3. Surgical iteration through keys to eliminate false positives
    for pos in positions:
        if not isinstance(pos, dict):
            continue
        
        # Check trading symbol specifically for the target option string
        tsym = str(pos.get("trading_symbol", pos.get("symbol", ""))).upper()
        if opt not in tsym:
            continue
            
        # Extract quantitative value from explicit position metric keys
        for key in ["netqty", "quantity", "qty", "net_quantity", "net_qty"]:
            if key in pos:
                try:
                    total_qty += abs(int(pos[key]))
                    break # Found quantitative key, move to next position object
                except (ValueError, TypeError):
                    pass
                    
    return total_qty


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
            print(f"{Fore.MAGENTA}🛑 NO-ACTION signal({entry_signal if entry_signal else 'BLANK'})-ACTION skipped")
            return

        # --- SESSION INITIALIZATION (Only runs for actionable signals) ---
        client = get_session()
        if not client:
            return

        ltp = data.get("price")

        try:
            supertrend = str(data.get("supertrend", "")).upper().strip()
            OTM_DISTANCE = 200
        except: 
            supertrend = "NONE"
            OTM_DISTANCE = 100

        exit_sig = str(reversal).upper().strip() if reversal else "NONE"
        if not entry_signal: return

        sig = entry_signal.upper().strip()
        if sig == "STBUY": sig = "ATMBUY"
        elif sig == "STSELL": sig = "ATMSELL"
        dprint(f"SIGNAL: {sig} | SUPERTREND BALANCER: {supertrend}")

        # --- POSITION BALANCING LOGIC (+1 CUSHION & PER-SIDE LIMITS) ---
        dprint("CHECKING POSITION STATE FOR STRATEGY ENFORCEMENT...")
        pos_raw = str(get_position_summary(client))
        
        ce_qty = parse_net_quantity(pos_raw, "CE")
        pe_qty = parse_net_quantity(pos_raw, "PE")
        
        current_ce_lots = ce_qty // LOT_SIZE if LOT_SIZE else 0
        current_pe_lots = pe_qty // LOT_SIZE if LOT_SIZE else 0
        
        dprint(f"CURRENT -> CE: {ce_qty} ({current_ce_lots} Lots) | PE: {pe_qty} ({current_pe_lots} Lots) | SIGNAL: {sig}")

        symbol, res = None, {"stat": "SKIPPED"}
        
        # 🟢 CE SIGNAL PROCESSING
        if sig in ["ATMBUY", "OTMBUY"]:
            is_balanced = False
            if supertrend == "BULL":
                is_balanced = ce_qty < (pe_qty + LOT_SIZE)
            else:
                is_balanced = ce_qty <= pe_qty  # Keep pace equally if supertrend doesn't match

            if is_balanced:
                if (current_ce_lots + 1) <= MAX_LOTS_PER_SIDE:
                    if not is_side_cooling("CE"):
                        symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                        if symbol and symbol != "NA":
                            res = execute_order(client, symbol, LOT_SIZE)
                            if res["stat"] == "OK": set_side_cooling("CE")
                else:
                    print(f"{Fore.RED}🛑 HARD BLOCK: Next CE order would exceed MAX CAPACITY ({MAX_LOTS_PER_SIDE} lots). Order blocked.")
            else:
                dprint(f"SKIP: CE({ce_qty}) cannot expand. Supertrend={supertrend} check failed against PE({pe_qty})", Fore.YELLOW)

        # 🔴 PE SIGNAL PROCESSING
        elif sig in ["ATMSELL", "OTMSELL"]:
            is_balanced = False
            if supertrend == "BEAR":
                is_balanced = pe_qty < (ce_qty + LOT_SIZE)
            else:
                is_balanced = pe_qty <= ce_qty  # Keep pace equally if supertrend doesn't match

            if is_balanced:
                if (current_pe_lots + 1) <= MAX_LOTS_PER_SIDE:
                    if not is_side_cooling("PE"):
                        symbol = get_symbol(ltp, sig, OTM_DISTANCE)
                        if symbol and symbol != "NA":
                            res = execute_order(client, symbol, LOT_SIZE)
                            if res["stat"] == "OK": set_side_cooling("PE")
                else:
                    print(f"{Fore.RED}🛑 HARD BLOCK: Next PE order would exceed MAX CAPACITY ({MAX_LOTS_PER_SIDE} lots). Order blocked.")
            else:
                dprint(f"SKIP: PE({pe_qty}) cannot expand. Supertrend={supertrend} check failed against CE({ce_qty})", Fore.YELLOW)

        # --- 📊 ACCOUNT DASHBOARD SUMMARY ---
        try:
            funds = get_available_funds(client)
        except:
            funds = 0

        print(f"""
 =====================================
         💰  Cash   : {int(funds)}
         📦  Pos    : {pos_raw}
         🎫  Symbol : {symbol if symbol else 'NONE'}
         🎯  Signal : {entry_signal}
         📌  Status : {res.get('stat')}
 =====================================
 """)

    except Exception as main_e:
        print(f"{Fore.RED}❌ CRITICAL ERROR IN MAIN loop: {main_e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

