#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime, time as dt_time
import pytz

# ---------------- PATH ----------------
HERE = Path(__file__).resolve().parent

def run_execprt():
    try:
        script_path = HERE / "execprtpxy.py"

        subprocess.run(
            [sys.executable, str(script_path)],
            check=True
        )
    except Exception as e:
        print(f"ERR execprt: {str(e)[:20]}")


# ---------------- TELEGRAM CONFIG ----------------
TELEGRAM_BOT_TOKEN = "7141714085:AAHlyEzszCy9N-L6wO1zSAkRwGdl0VTQCFI"
TELEGRAM_CHAT_ID   = "-4282665161"

def send_telegram(msg):
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
        print(f"TG ERR: {str(e)[:25]}")


# ---------------- IST TIMEZONE ----------------
IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN  = dt_time(9, 16)
MARKET_CLOSE = dt_time(15, 25)

def now_ist():
    return datetime.now(IST)

def is_market_hours():
    now_dt = now_ist()
    t = now_dt.time()
    wd = now_dt.weekday()
    return 0 <= wd <= 4 and MARKET_OPEN <= t < MARKET_CLOSE


# ---------------- SUPERVISOR LOOP ----------------
def start_loop():
    run_execprt()   # run once

    was_open = False
    off_done = False
    EXE_FILE = HERE / "exepxy.py"

    while True:
        t0 = time.time()
        mkt = is_market_hours()

        # ---- MARKET OPEN ----
        if mkt and not was_open:
            send_telegram("Bot started (market open)")
            print("MKT OPEN: bot started")
            off_done = False

        # ---- MARKET CLOSE ----
        if not mkt and was_open:
            send_telegram("Bot stopped (market close)")
            print("MKT CLOSE: bot stopped")
            off_done = False

        # ---- RUN MAIN ----
        if mkt:
            subprocess.run([sys.executable, str(EXE_FILE)])
        else:
            if not off_done:
                print("Off-mkt run once")
                subprocess.run([sys.executable, str(EXE_FILE)])
                off_done = True

        was_open = mkt
        time.sleep(max(0, 1 - (time.time() - t0)))


# ---------------- ENTRY ----------------
if __name__ == "__main__":
    start_loop()
