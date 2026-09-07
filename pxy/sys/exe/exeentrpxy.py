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

# --- GLOBAL CONFIG ---
DEBUG = True  # FORCED TRUE to enable complete scannable runtime visibility
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
            # Absolute workspace layout mapping to prevent directory drifting
            file_path = RUN_DIR / f"exebal_cool_{side}.txt"
            if file_path.exists():
                try:
                    file_path.unlink()
                    dprint(f"Daily Reset: Cleared lock framework target {file_path.name}", Fore.YELLOW)
                except: pass

def is_side_cooling(side):
    file_path = RUN_DIR / f"exebal_cool_{side.lower()}.txt"
    if not file_path.exists():
        return False
    try:
        with open(file_path, "r") as f:
            last_ts = float(f.read().strip())
            elapsed = time.time() - last_ts
            if elapsed < COOL_DOWN_SECONDS:
                dprint(f"{side.upper()} is COOLING. {int(COOL_DOWN_SECONDS - elapsed)}s remaining.", Fore.WHITE)
                return True
            file_path.unlink()
            dprint(f"{side.upper()} cooling threshold expired. Lock erased.", Fore.CYAN)
            return False
    except: return False

def set_side_cooling(side):
    file_path = RUN_DIR / f"exebal_cool_{side.lower()}.txt"
    with open(file_path, "w") as f:
        f.write(str(time.time()))
    dprint(f"Cooling lock ENGAGED safely for {side.upper()}.", Fore.YELLOW)

# --- SYSTEM INTEGRATION MODULE VERIFICATION ---
dprint("IMPORTING MODULE INTEGRATION SCHEMAS...")
try:
    from syspxy import get_all_data
    from execepepxy import get_target_quantities 
    from runclntpxy import get_session
    from runfundpxy import get_available_funds
    from runpchkpxy import get_position_summary
    from runsymbpxy import get_symbol
    dprint("ALL ENTRY INTERFACES LOADED SUCCESSFULLY", Fore.GREEN)
except Exception as e:
    print(f"{Fore.RED}CRITICAL SUBSYSTEM IMPORT ERROR: {e}")
    print(traceback.format_exc())
    sys.exit(1)

# --- Updated Tag Generator for Day Trading ---
def generate_pxy_tag():
    """Generates a pure timestamp tag string: HHMMSS"""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).strftime('%H%M%S')
def execute_order(client, symbol, qty):
    dprint(f"ENTER execute_order for {symbol}")
    try:
        order_tag = generate_pxy_tag()
        
        # Protective Limit execution ceiling baseline for un-traded option instruments
        fallback_limit_price = 5.00
        
        # Enforcing 'L' string parameters to stay compliant with Neo SDK whitelist constraints
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": f"{fallback_limit_price:.2f}",
            "order_type": "L",  
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": "B",
            "amo": "NO",
            "tag": order_tag
        }
        
        dprint(f"DISPATCHING COMPILING PAYLOAD PARAMS: {params}", Fore.YELLOW)
        res = client.place_order(**params)
        
        print(f"{Fore.CYAN}        🚀 {symbol} | {order_tag}")
        print(f"{Fore.MAGENTA}📬 [DEBUG] RAW ORDER RESPONSE CONSOLE DICT: {res}")
        
        # Comprehensive status tracking mapping to catch hidden rejections
        is_valid_success = False
        if isinstance(res, dict):
            stat_flag = str(res.get("stat", "")).upper()
            err_msg = str(res.get("errMsg", "")).lower()
            if (stat_flag == "OK" or res.get("stCode") == 0) and "rejected" not in err_msg:
                is_valid_success = True
        
        return {"stat": "OK" if is_valid_success else "FAIL", "raw": res}
    except Exception as e:
        print(f"{Fore.RED}💥 [EXECUTE ARCHITECTURE ERROR] Execution crash within order block: {e}")
        if DEBUG:
            print(traceback.format_exc())
        return {"stat": "FAIL", "err": str(e)}
async def main():
    dprint("===== MAIN BALANCING LOOP INITIALIZED =====", Fore.GREEN)
    try:
        reset_daily_cooling()
        IST = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(IST)
        now = now_ist.time()
        dprint(f"TIME FRAME CHECK: {now}")

        # 1. Check Market Timing First
        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 11) <= now < dt_time(15, 50)):
            print(f"{Fore.YELLOW}⏳ Market buffer time restriction encountered - skipping cycle")
            return

        # 2. Fetch Data and Check Signal Status
        data = get_all_data()
        dprint(f"RAW UPSTREAM INCOMING PAYLOAD: {data}", Fore.WHITE)
        entry_signal = str(data.get("entry", "")).upper().strip()
        reversal = data.get("exit")

        if entry_signal in ["BULL", "BEAR", "NONE", "WAIT", ""]:
            print(f"{Fore.MAGENTA}🛑 NO-ACTION signal condition ({entry_signal if entry_signal else 'BLANK'})- execution halted")
            return

        # --- SESSION INITIALIZATION (Runs strictly for qualified signal markers) ---
        dprint("VERIFYING LIVE CONNECTIONS...")
        client = get_session()
        if not client:
            print(f"{Fore.RED}❌ Authentication context returned empty framework structure.")
            return

        # Pure numerical calculation reference anchor
        spot_reference_price = float(data.get("price", 0))
        dprint(f"BASE VALUATION POINT: {spot_reference_price}", Fore.WHITE)

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
            dprint(f"CALCULATED WORKSPACE OTM DISTANCE: {OTM_DISTANCE} (Day: {current_day}, Buffer: {x})")
        except Exception as e: 
            dprint(f"SUPERTREND DICTIONARY PARSE EXCEPTION: {e}", Fore.YELLOW)
            supertrend_val = "NONE"
            OTM_DISTANCE = 100

        exit_sig = str(reversal).upper().strip() if reversal else "NONE"
        if not entry_signal: return

        sig = entry_signal.upper().strip()
        if sig == "STBUY": sig = "ATMBUY"
        elif sig == "STSELL": sig = "ATMSELL"
        dprint(f"SIGNAL ROUTING TAG EVALUATED: {sig}")
        
        # --- POSITION INTEGRITY LOOKUPS ---
        dprint("EVALUATING ACTIVE PORTFOLIO BALANCE SCHEMA...")
        pos_raw = str(get_position_summary(client)).upper().strip() 
        dprint(f"RAW ACTIVE POSITION PACKETS: '{pos_raw}'", Fore.WHITE)
        
        match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
        if match:
            ce_lots = int(match.group(1))
            pe_lots = int(match.group(2))
        else:
            dprint(f"⚠️ Pos layout signature structure variant: '{pos_raw}'. Defaulting counters to zero.", Fore.YELLOW)
            ce_lots, pe_lots = 0, 0
        
        dprint(f"METRICS ANALYSIS -> CE LOT COUNTS: {ce_lots} | PE LOT COUNTS: {pe_lots}")
        
        max_allowed_ce_lots, max_allowed_pe_lots = get_target_quantities(supertrend_val, ce_lots, pe_lots, LOT_SIZE)
        dprint(f"STRATEGY PARAMS -> MAX CE BLOCKS: {max_allowed_ce_lots} | MAX PE BLOCKS: {max_allowed_pe_lots}")

        if "ATM" in sig:
            current_distance = 0
        elif "OTM" in sig:
            current_distance = OTM_DISTANCE
        else:
            current_distance = 0

        dprint(f"RESOLVING STRIKE FOR RE-ROUTING -> SIG: {sig} | DISTANCE: {current_distance}")
        symbol, res = None, {"stat": "SKIPPED"}
        is_flat_bypass = (ce_lots == 0 and pe_lots == 0)

        # --- CALL CONDITION ROUTER ---
        if sig in ["ATMBUY", "OTMBUY"]:
            dprint("PROCESSING CONDITION TREE: BALANCE CE")
            if is_flat_bypass or (ce_lots < max_allowed_ce_lots) or (ce_lots == 0 and pe_lots == 0 and max_allowed_ce_lots > 0):
                if not is_side_cooling("CE"):
                    symbol = get_symbol(spot_reference_price, sig, current_distance)
                    dprint(f"TARGET DEPLOYED CONTRACT STRING: '{symbol}'", Fore.WHITE)
                    if symbol and symbol != "NA":
                        # Subprocess execution channel for persistent token indexing
                        sub_path = RUN_DIR / "runtknltppxy.py"
                        print(f"{Fore.CYAN}🔍 Invoking background contract validator for: {symbol}")
                        sub_run = subprocess.run([sys.executable, str(sub_path), symbol], capture_output=True, text=True)
                        
                        dprint(f"SUBPROCESS SYSTEM LOGOUT:\n{sub_run.stdout}", Fore.WHITE)
                        if sub_run.stderr:
                            print(f"{Fore.RED}💥 SUBPROCESS STACKTRACE REJECTIONS:\n{sub_run.stderr}")
                        
                        # Parsing derived token metrics
                        json_path = RUN_DIR / "nftfut.json"
                        with open(json_path, "r") as f:
                            ltp = float(json.load(f).get("price", 0))
                        print(f"{Fore.GREEN}🎯 Premium option target context resolved: {ltp:.2f}")
                        
                        res = execute_order(client, symbol, LOT_SIZE)
                        dprint(f"DISPATCH RESPONSE BUNDLE SUMMARY: {res}", Fore.WHITE)
                        if res["stat"] == "OK": 
                            set_side_cooling("CE")
                else:
                    print(f"{Fore.YELLOW}⏳ Halted -> CE side lock cooling is actively operational.")
            else:
                dprint(f"SKIP: CE Lots ({ce_lots}) hit or exceeded strategy limit ({max_allowed_ce_lots})", Fore.YELLOW)

        # --- PUT CONDITION ROUTER ---
        elif sig in ["ATMSELL", "OTMSELL"]:
            dprint("PROCESSING CONDITION TREE: BALANCE PE")
            if is_flat_bypass or (pe_lots < max_allowed_pe_lots) or (ce_lots == 0 and pe_lots == 0 and max_allowed_pe_lots > 0):
                if not is_side_cooling("PE"):
                    symbol = get_symbol(spot_reference_price, sig, current_distance)
                    dprint(f"TARGET DEPLOYED CONTRACT STRING: '{symbol}'", Fore.WHITE)
                    if symbol and symbol != "NA":
                        # Subprocess execution channel for persistent token indexing
                        sub_path = RUN_DIR / "runtknltppxy.py"
                        print(f"{Fore.CYAN}🔍 Invoking background contract validator for: {symbol}")
                        sub_run = subprocess.run([sys.executable, str(sub_path), symbol], capture_output=True, text=True)
                        
                        dprint(f"SUBPROCESS SYSTEM LOGOUT:\n{sub_run.stdout}", Fore.WHITE)
                        if sub_run.stderr:
                            print(f"{Fore.RED}💥 SUBPROCESS STACKTRACE REJECTIONS:\n{sub_run.stderr}")
                        
                        # Parsing derived token metrics
                        json_path = RUN_DIR / "nftfut.json"
                        with open(json_path, "r") as f:
                            ltp = float(json.load(f).get("price", 0))
                        print(f"{Fore.GREEN}🎯 Premium option target context resolved: {ltp:.2f}")
                        
                        res = execute_order(client, symbol, LOT_SIZE)
                        dprint(f"DISPATCH RESPONSE BUNDLE SUMMARY: {res}", Fore.WHITE)
                        if res["stat"] == "OK": 
                            set_side_cooling("PE")
                else:
                    print(f"{Fore.YELLOW}⏳ Halted -> PE side lock cooling is actively operational.")
            else:
                dprint(f"SKIP: PE Lots ({pe_lots}) hit or exceeded strategy limit ({max_allowed_pe_lots})", Fore.YELLOW)

        funds = get_available_funds(client)
        dprint(f"POST-LOOP CLEARING MARGIN BALANCE: {funds}", Fore.WHITE)

        print(f"""
 ============ BUY ACTION SUMMARY =============
         🎯  Signal Assessment : {entry_signal}
         📈  Trend Classification  : {supertrend_val}
         📦  Portfolio Matrix  : {pos_raw}
         📌  Execution Status  : {res.get('stat')}
 ==============================================
 """)
        dprint("===== ENGINE CYCLE PROCESS COMPLETE =====", Fore.GREEN)
    except Exception:
        print(f"{Fore.RED}💥 UNCAUGHT SYSTEM EXCEPTION WITHIN CORE EXECUTION ARCHITECTURE:")
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())

