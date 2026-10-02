import sys
import os
import pytz
import traceback
import re
from pathlib import Path
from datetime import datetime, time as dt_time
from colorama import Fore, init, Style

# --- GLOBAL CONFIG ---
DEBUG = False

init(autoreset=True)

# --- PATH SETUP ---
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
RUN_DIR = HERE / "run"
for p in [HERE, RUN_DIR, PARENT]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

def dprint(msg, color=Fore.CYAN):
    if DEBUG:
        print(f"{Style.BRIGHT}{color}[DBUG] {msg[:35]}{Style.RESET_ALL}")

dprint("IMPORTING...")
try:
    from syspxy import get_all_data
    from runclntpxy import get_session
    from runpchkpxy import get_position_summary

    dprint("IMPORTS OK", Fore.GREEN)
except Exception as e:
    print(f"{Fore.RED}IMP ERR: {str(e)[:30]}")
    sys.exit(1)


def main():
    dprint("===== START =====", Fore.GREEN)
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist).time()
        dprint(f"TIME: {now}")

        # 1. Market Timing Validation
        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (
            dt_time(15, 11) <= now < dt_time(15, 50)
        ):
            print(f"{Fore.YELLOW}⏳ Market buffer time - skip")
            return

        # 2. Central Entry Signal Verification
        data = get_all_data()
        entry_signal = data.get("entry")

        if not isinstance(entry_signal, str) or entry_signal not in ("BUY", "SELL"):
            rejected_signal = str(entry_signal)[:10]
            print(f"{Fore.YELLOW}⏳ Skip {rejected_signal}: Invalid entry signal")
            return

        # 3. Session Initialization
        client = get_session()
        if not client:
            print(f"{Fore.RED}❌ Session failed; entry skipped.")
            return

        dprint(f"SIG OK: {entry_signal}")

        # 4. Position Check — proceed only on a confirmed flat result
        dprint("CHECKING POS...")
        pos_raw = get_position_summary(client)

        if not isinstance(pos_raw, str):
            print(f"{Fore.YELLOW}⚠️ Position check failed; skipping this entry run.")
            return

        match = re.fullmatch(r"(\d+)CE(\d+)PE", pos_raw.upper().strip())
        if not match:
            print(f"{Fore.YELLOW}⚠️ Invalid position result; skipping this entry run.")
            return

        ce_lots = int(match.group(1))
        pe_lots = int(match.group(2))
        dprint(f"CE: {ce_lots} | PE: {pe_lots}")

        if ce_lots != 0 or pe_lots != 0:
            print(
                f"{Fore.YELLOW}⚠️ Position open (CE:{ce_lots}, PE:{pe_lots}); "
                "entry skipped."
            )
            return

        # 5. Route a signal only after pchk confirms both sides are flat
        if entry_signal == "BUY":
            print(
                f"{Fore.GREEN}{Style.BRIGHT}"
                "🟢 FRESH ENTRY: Firing command 'pxybuyce'..."
            )
            result = os.system("pxybuyce")
            if result != 0:
                print(f"{Fore.RED}⚠️ pxybuyce exited with status {result}.")

        elif entry_signal == "SELL":
            print(
                f"{Fore.GREEN}{Style.BRIGHT}"
                "🟢 FRESH ENTRY: Firing command 'pxybuype'..."
            )
            result = os.system("pxybuype")
            if result != 0:
                print(f"{Fore.RED}⚠️ pxybuype exited with status {result}.")

        dprint("===== END =====", Fore.GREEN)

    except Exception:
        print(traceback.format_exc() if DEBUG else "❌ Error encountered; entry skipped.")


if __name__ == "__main__":
    main()
