import sys
import os
import traceback
import re
from pathlib import Path
from datetime import datetime
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

from syscnfgpxy import (
    EXEENTRPXY_ENTRY_CUTOFF,
    EXEENTRPXY_PREOPEN_END,
    EXEENTRPXY_PREOPEN_START,
    EXEENTRPXY_SQUAREOFF_END,
    SYSCNFGPXY_TIMEZONE,
)

def dprint(msg, color=Fore.CYAN):
    if DEBUG:
        print(f"{Style.BRIGHT}{color}[DBUG] {msg[:35]}{Style.RESET_ALL}")

dprint("IMPORTING...")
try:
    from syspxy import get_all_data
    from runclntpxy import get_session
    from runpchkpxy import get_position_summary
    from sysmodepxy import dispatch_mode
    from sysdecisionpxy import entry_order_command

    dprint("IMPORTS OK", Fore.GREEN)
except Exception as e:
    print(f"{Fore.RED}IMP ERR: {str(e)[:30]}")
    sys.exit(1)


def main():
    dprint("===== START =====", Fore.GREEN)
    if not dispatch_mode("engine_window_open", lambda: True):
        print(f"{Fore.YELLOW}TST engine paused during market hours; entry pipe not run.")
        return
    try:
        now = datetime.now(SYSCNFGPXY_TIMEZONE).time()
        dprint(f"TIME: {now}")

        # 1. Market Timing Validation
        is_blackout = lambda now: (
            (EXEENTRPXY_PREOPEN_START <= now < EXEENTRPXY_PREOPEN_END)
            or (EXEENTRPXY_ENTRY_CUTOFF <= now < EXEENTRPXY_SQUAREOFF_END)
        )
        if dispatch_mode("is_entry_blackout", is_blackout, now):
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

        command = entry_order_command(entry_signal, ce_lots, pe_lots)
        if command is None:
            print(
                f"{Fore.YELLOW}⚠️ Position open (CE:{ce_lots}, PE:{pe_lots}); "
                "entry skipped."
            )
            return

        # 5. Route a signal only after pchk confirms both sides are flat
        print(
            f"{Fore.GREEN}{Style.BRIGHT}"
            f"🟢 FRESH ENTRY: Firing command '{command}'..."
        )
        result = os.system(command)
        if result != 0:
            print(f"{Fore.RED}⚠️ {command} exited with status {result}.")

        dprint("===== END =====", Fore.GREEN)

    except Exception:
        print(traceback.format_exc() if DEBUG else "❌ Error encountered; entry skipped.")


if __name__ == "__main__":
    main()
