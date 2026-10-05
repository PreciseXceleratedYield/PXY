#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from datetime import datetime
from syscnfgpxy import (
    SYSEXEPXY_MARKET_CLOSE,
    SYSEXEPXY_MARKET_OPEN,
    SYSEXEPXY_SUPERVISOR_INTERVAL_SECONDS,
    SYSMODEPXY_RUN_MODE as RUNMODE,
    SYSCNFGPXY_TIMEZONE,
)
from sysmodepxy import dispatch_mode, normal_start_message

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
IST = SYSCNFGPXY_TIMEZONE

def now_ist():
    """Return current IST datetime"""
    return datetime.now(IST)

def _is_market_hours_production():
    """Check if current time is within market hours"""
    now_dt = now_ist()
    t = now_dt.time()
    wd = now_dt.weekday()
    return (
        0 <= wd <= 4
        and SYSEXEPXY_MARKET_OPEN <= t < SYSEXEPXY_MARKET_CLOSE
    )


def is_market_hours():
    return dispatch_mode("engine_window_open", _is_market_hours_production)

# ---------------- SUPERVISOR LOOP ----------------
def start_loop():
    """Main loop to supervise execution"""
    if RUNMODE != "PRD":
        print(normal_start_message(RUNMODE), file=sys.stderr)
        return 2

    if dispatch_mode("run_startup_checks", lambda: True):
        run_execprt()
    was_open = False
    off_done = False

    # Adjusted path to child directory
    EXE_FILE = os.path.join("exe", "exepxy.py")

    while True:
        t0 = time.time()
        mkt = is_market_hours()

        # ---- MARKET OPEN ----
        if mkt and not was_open:
            send_telegram("Bot started (engine window open)")
            print("🚀 ENGINE WINDOW OPEN: bot started 📡")
            off_done = False

        # ---- MARKET CLOSE ----
        if not mkt and was_open:
            send_telegram("Bot paused (engine window closed)")
            print("🛑 ENGINE WINDOW CLOSED: bot paused 🔒")
            off_done = False

        # ---- RUN MAIN SCRIPT ----
        if os.path.exists(EXE_FILE):
            if mkt:
                subprocess.run([sys.executable, EXE_FILE])
            elif dispatch_mode("run_closed_market_tasks", lambda: True):
                if not off_done:
                    print("🌙 OFF MKT: one run executed, idle now 💤")
                    subprocess.run([sys.executable, EXE_FILE])
                    off_done = True
            else:
                print("CHK MODE: whole engine paused during market hours.")
        else:
            print("❌ EXE ERR: exepxy.py file not found ⚠️")

        was_open = mkt
        time.sleep(
            max(
                0,
                SYSEXEPXY_SUPERVISOR_INTERVAL_SECONDS - (time.time() - t0),
            )
        )

# ---------------- ENTRY POINT ----------------
if __name__ == "__main__":
    start_loop()
