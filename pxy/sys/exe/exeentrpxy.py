import sys
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

init(autoreset=True)

# --- PATH SETUP ---
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
RUN_DIR = HERE / "run"
for p in [HERE, RUN_DIR, PARENT]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from syscnfgpxy import TICKER

# --- LOT SIZE LOGIC ---
t = TICKER.upper().strip()
LOT_SIZE = 30 if t == "^NSEBANK" else 65 if t == "^NSEI" else None

def dprint(msg, color=Fore.CYAN):
    if DEBUG:
        print(f"{Style.BRIGHT}{color}[DBUG] {msg[:35]}{Style.RESET_ALL}")

dprint("IMPORTING...")
try:
    from syspxy import get_all_data
    from execepepxy import get_target_quantities 
    from runclntpxy import get_session
    from runpchkpxy import get_position_summary
    dprint("IMPORTS OK", Fore.GREEN)
except Exception as e:
    print(f"{Fore.RED}IMP ERR: {str(e)[:30]}"); sys.exit(1)


def main():
    dprint("===== START =====", Fore.GREEN)
    try:
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()
        dprint(f"TIME: {now}")

        # 1. Market Timing Validation
        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 11) <= now < dt_time(15, 50)):
            print(f"{Fore.YELLOW}⏳ Market buffer time - skip")
            return

        # 2. Central Entry Signal Verification
        data = get_all_data()
        entry_signal = str(data.get("entry", "")).upper().strip()

        if entry_signal in ["BULL", "BEAR", "NONE", "WAIT", ""]:
            print(f"{Fore.MAGENTA}🛑 No-Action ({entry_signal[:10]}) - skip")
            return

        # Top-Level Condition: Force check for ATM/OTM keywords
        if "ATM" not in entry_signal and "OTM" not in entry_signal:
            print(f"{Fore.YELLOW}⏳ Skip {entry_signal[:10]}: No ATM/OTM")
            return

        # 3. Session Initialization
        client = get_session()
        if not client:
            print(f"{Fore.RED}❌ Session failed")
            return

        sig = entry_signal.upper().strip()
        if sig == "STBUY": sig = "ATMBUY"
        elif sig == "STSELL": sig = "ATMSELL"
        
        dprint(f"SIG OK: {sig}")

        # 4. Position Extraction
        dprint("CHECKING POS...")
        pos_raw = str(get_position_summary(client)).upper().strip() 
        
        match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
        if match:
            ce_lots = int(match.group(1))
            pe_lots = int(match.group(2))
        else:
            dprint("Layout error, use 0", Fore.YELLOW)
            ce_lots, pe_lots = 0, 0
        
        dprint(f"CE: {ce_lots} | PE: {pe_lots}")
        
        # Upfront Gate: CE PE Weight Check
        if ce_lots >= 1 and pe_lots >= 1:
            print(f"{Fore.YELLOW}⚠️  CE|PE Weighted already,handing to AVG")
            return

        # 5. Maximum Strategy Lot Allocation Check
        max_ce, max_pe = get_target_quantities(ce_lots, pe_lots, LOT_SIZE)
        dprint(f"MAX C:{max_ce} | P:{max_pe}")

        is_flat = (ce_lots == 0 and pe_lots == 0)

        # 6. Routing Engine (Matching exact execution framework of your reference code)
        if "BUY" in sig:
            dprint("BRANCH: CE")
            if is_flat or (ce_lots < max_ce):
                print(f"{Fore.GREEN}{Style.BRIGHT}🟢 FRESH ENTRY: Firing command 'pxybuyce'...")
                try:
                    os.system("pxybuyce")
                except Exception as e:
                    print(f"{Fore.RED}⚠️ Failed to execute pxybuyce: {e}")
            else:
                dprint("CE limit hit", Fore.YELLOW)

        elif "SELL" in sig:
            dprint("BRANCH: PE")
            if is_flat or (pe_lots < max_pe):
                print(f"{Fore.GREEN}{Style.BRIGHT}🟢 FRESH ENTRY: Firing command 'pxybuype'...")
                try:
                    os.system("pxybuype")
                except Exception as e:
                    print(f"{Fore.RED}⚠️ Failed to execute pxybuype: {e}")
            else:
                dprint("PE limit hit", Fore.YELLOW)

        dprint("===== END =====", Fore.GREEN)
    except Exception:
        print(traceback.format_exc() if DEBUG else "❌ Error encountered")


if __name__ == "__main__":
    main()

