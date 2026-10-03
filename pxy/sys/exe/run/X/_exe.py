#!/usr/bin/env python3
# _exe.py
import os
import sys
import time
import subprocess
from datetime import datetime, time as dt_time
import pytz
from colorama import init, Fore, Style
from _sgnl import _pad_line_to_42  # Shared 42-character width constraint engine
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[3]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))
from syscnfgpxy import RUNMODE

init(autoreset=True)

# =====================================================================
# 1. INTEGRATED TELEGRAM ALERT INTERFACE
# =====================================================================
TELEGRAM_BOT_TOKEN = "7141714085:AAHlyEzszCy9N-L6wO1zSAkRwGdl0VTQCFI"
TELEGRAM_CHAT_ID   = "-4282665161"

def send_telegram(msg):
    """Dispatches secure live state warnings to your Telegram channel."""
    url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        import requests
        requests.post(url, data=payload, timeout=5)
    except Exception:
        err_msg = "📡 TG ERR: Notification fail ⚠️"
        print(_pad_line_to_42(err_msg, Fore.YELLOW, Style.RESET_ALL))

# =====================================================================
# 2. IST TIMEZONE AND HOURS PROFILE MONITOR
# =====================================================================
IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN  = dt_time(9, 16)
MARKET_CLOSE = dt_time(15, 25)

def now_ist():
    return datetime.now(IST)

def is_market_hours():
    """Evaluates strict operational timing parameters (Mon-Fri)."""
    if RUNMODE == "TST":
        return True
    now_dt = now_ist()
    t = now_dt.time()
    wd = now_dt.weekday()
    return 0 <= wd <= 4 and MARKET_OPEN <= t < MARKET_CLOSE

# =====================================================================
# 3. LIVE SUPERVISOR GUARD DAEMON
# =====================================================================
def start_loop():
    """Monitors trading states and acts as a shield wrapper for _sys.py."""
    EXE_FILE = "_sys.py"
    border = "==========================================" # 42 chars

    print(f"\n{_pad_line_to_42(border, Fore.GREEN, Style.RESET_ALL)}")
    print(_pad_line_to_42("📌 STAGE 1: Mandatory Initial Startup Run", Fore.GREEN + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42(border, Fore.GREEN, Style.RESET_ALL))
    
    # ---- MANDATORY FIRST RUN AT STARTUP ----
    if os.path.exists(EXE_FILE):
        sync_msg = f"🔄 Initial sync scan: {EXE_FILE}"
        print(_pad_line_to_42(sync_msg, Fore.WHITE, Style.RESET_ALL))
        subprocess.run([sys.executable, EXE_FILE])
        print(_pad_line_to_42("✅ Startup sync cycle complete", Fore.GREEN, Style.RESET_ALL))
    else:
        err_msg = f"❌ EXE ERR: Missing target script {EXE_FILE}"
        print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))
        sys.exit(1)

    print(f"\n{_pad_line_to_42(border, Fore.YELLOW, Style.RESET_ALL)}")
    print(_pad_line_to_42("🏁 STAGE 2: Supervisor Loop Matrix Active", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
    print(_pad_line_to_42(border, Fore.YELLOW, Style.RESET_ALL))

    was_open = is_market_hours()
    off_done = not was_open 

    while True:
        t0 = time.time()
        mkt = is_market_hours()

        # ---- BOUNDARY TRANSITION: MARKET OPEN ----
        if mkt and not was_open:
            send_telegram("<b>Bot started (market open)</b>")
            print(_pad_line_to_42("🚀 MKT OPEN: Starting trading daemon 📡", Fore.GREEN, Style.RESET_ALL))
            off_done = False

        # ---- BOUNDARY TRANSITION: MARKET CLOSE ----
        if not mkt and was_open:
            send_telegram("<b>Bot stopped (market close)</b>")
            print(_pad_line_to_42("🛑 MKT CLOSE: Throttling trading core 🔒", Fore.RED, Style.RESET_ALL))
            off_done = False

        # ---- TARGET SUBPROCESS MANAGEMENT GATE ----
        if mkt:
            subprocess.run([sys.executable, EXE_FILE])
        else:
            if not off_done:
                print(_pad_line_to_42("🌙 OFF MKT: Maintenance session run 💤", Fore.BLUE, Style.RESET_ALL))
                subprocess.run([sys.executable, EXE_FILE])
                off_done = True

        was_open = mkt
        time.sleep(max(0, 1 - (time.time() - t0)))

# =====================================================================
# 4. ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    try:
        start_loop()
    except KeyboardInterrupt:
        print(f"\n{_pad_line_to_42('🛑 Supervisor halted via exit command', Fore.YELLOW, Style.RESET_ALL)}")
        sys.exit(0)
