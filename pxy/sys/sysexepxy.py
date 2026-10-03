#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from datetime import datetime, time as dt_time
import pytz
from syscnfgpxy import RUNMODE

# ---------------- EXEC SCRIPT ----------------
def run_execprt():
    """Run execprtpxy.py once at startup"""
    script_path = "syscprtpxy.py"
    if not os.path.exists(script_path):
        print("❌ EXECPRT ERR: file not found ⚠️")
        return
    try:
        subprocess.run([sys.executable, script_path], check=True)
    except Exception as e:
        print("❌ EXECPRT ERR: run failed ⚠️")

# ---------------- TELEGRAM CONFIG ----------------
TELEGRAM_BOT_TOKEN = "7141714085:AAHlyEzszCy9N-L6wO1zSAkRwGdl0VTQCFI"
TELEGRAM_CHAT_ID   = "-4282665161"

def send_telegram(msg):
    """Send Telegram notification"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        import requests
        requests.post(url, data=payload)
    except Exception as e:
        print("📡 TG ERR: message send failed ⚠️")

# ---------------- IST TIMEZONE ----------------
IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN  = dt_time(9, 16)
MARKET_CLOSE = dt_time(15, 45)

def now_ist():
    """Return current IST datetime"""
    return datetime.now(IST)

def is_market_hours():
    """Check if current time is within market hours"""
    if RUNMODE == "TST":
        return True
    now_dt = now_ist()
    t = now_dt.time()
    wd = now_dt.weekday()
    return 0 <= wd <= 4 and MARKET_OPEN <= t < MARKET_CLOSE

# ---------------- SUPERVISOR LOOP ----------------
def start_loop():
    """Main loop to supervise execution"""
    run_execprt()   # run execprt once at start
    was_open = False
    off_done = False

    # Adjusted path to child directory
    EXE_FILE = os.path.join("exe", "exepxy.py")

    while True:
        t0 = time.time()
        mkt = is_market_hours()

        # ---- MARKET OPEN ----
        if mkt and not was_open:
            send_telegram("Bot started (market open)")
            print("🚀 MKT OPEN: bot started, ready trade 📡")
            off_done = False

        # ---- MARKET CLOSE ----
        if not mkt and was_open:
            send_telegram("Bot stopped (market close)")
            print("🛑 MKT CLOSE: bot stopped, session end 🔒")
            off_done = False

        # ---- RUN MAIN SCRIPT ----
        if os.path.exists(EXE_FILE):
            if mkt:
                subprocess.run([sys.executable, EXE_FILE])
            else:
                if not off_done:
                    print("🌙 OFF MKT: one run executed, idle now 💤")
                    subprocess.run([sys.executable, EXE_FILE])
                    off_done = True
        else:
            print("❌ EXE ERR: exepxy.py file not found ⚠️")

        was_open = mkt
        time.sleep(max(0, 1 - (time.time() - t0)))  # ~1s loop

# ---------------- ENTRY POINT ----------------
if __name__ == "__main__":
    start_loop()
