#!/usr/bin/env python3
# _exe.py
import os
import sys
import time
import subprocess
from datetime import datetime, time as dt_time
import pytz

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
        print("📡 TG ERR: Notification transmission failure ⚠️")

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
    now_dt = now_ist()
    t = now_dt.time()
    wd = now_dt.weekday()
    return 0 <= wd <= 4 and MARKET_OPEN <= t < MARKET_CLOSE

# =====================================================================
# 3. LIVE SUPERVISOR GUARD DAEMON
# =====================================================================
def start_loop():
    """Monitors trading states and acts as a shield wrapper for _sys.py."""
    was_open = False
    off_done = False

    # TARGET EXECUTABLE FILE PATH: Points directly flat to your automated loop orchestrator
    EXE_FILE = "_sys.py"

    print(f"🛡️ SUPERVISOR ACTIVE: Guarding flat file target node -> {EXE_FILE}")
    print("━" * 68)

    while True:
        t0 = time.time()
        mkt = is_market_hours()

        # ---- BOUNDARY TRANSITION: MARKET OPEN ----
        if mkt and not was_open:
            send_telegram("<b>Bot started (market open)</b>")
            print("🚀 MKT OPEN: Supervisor starting trading daemon arrays 📡")
            off_done = False

        # ---- BOUNDARY TRANSITION: MARKET CLOSE ----
        if not mkt and was_open:
            send_telegram("<b>Bot stopped (market close)</b>")
            print("🛑 MKT CLOSE: Supervisor throttling trading channels 🔒")
            off_done = False

        # ---- TARGET SUBPROCESS MANAGEMENT GATE ----
        if os.path.exists(EXE_FILE):
            if mkt:
                # If within active live trading parameters, run your loop master script
                subprocess.run([sys.executable, EXE_FILE])
            else:
                if not off_done:
                    print("🌙 OFF MKT: Executing single maintenance session scan, idling now 💤")
                    subprocess.run([sys.executable, EXE_FILE])
                    off_done = True
        else:
            print(f"❌ EXE ERR: Core pipeline orchestrator '{EXE_FILE}' missing from directory ⚠️")
            time.sleep(5)  # Throttle terminal alert logging spam

        was_open = mkt
        # Holds a flat, balanced 1-second ticks evaluation pacing frequency loop
        time.sleep(max(0, 1 - (time.time() - t0)))

# =====================================================================
# 4. ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    try:
        start_loop()
    except KeyboardInterrupt:
        print("\n🛑 Supervisor process halted via system interrupt command. Exiting.")
        sys.exit(0)
