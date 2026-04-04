#!/usr/bin/env python3
import os
import sys
import time
import pytz
import subprocess
from datetime import datetime, time as dt_time

# ---------------- CONFIG ----------------
IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN  = dt_time(9, 16)
MARKET_CLOSE = dt_time(15, 20)  # adjust stop time here
TELEGRAM_BOT_TOKEN = "7141714085:AAHlyEzszCy9N-L6wO1zSAkRwGdl0VTQCFI"
TELEGRAM_CHAT_ID   = "-4282665161"

# ---------------- FILES ----------------
EXEC_PRT_FILE = "execprtpxy.py"
EXE_ENT_FILE  = "exeentrpxy.py"
EXE_EXIT_FILE = "exeexitpxy.py"
EXE_SELF_FILE = "exeslefpxy.py"

# ---------------- CE/PE MOCK ----------------
try:
    from runpchkpxy import get_position_summary
except Exception as e:
    print(f"[WARN] Cannot import get_position_summary: {e}")
    get_position_summary = lambda: "0CE0PE"

# ---------------- HELPERS ----------------
def now_ist():
    return datetime.now(IST)

def is_market_hours():
    now = now_ist()
    wd = now.weekday()
    return 0 <= wd <= 4 and MARKET_OPEN <= now.time() < MARKET_CLOSE

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        import requests
        requests.post(url, data=payload)
    except Exception as e:
        print(f"TG ERR: {str(e)[:25]}")

def run_script(script_name):
    if os.path.exists(script_name):
        try:
            subprocess.run([sys.executable, script_name], check=True)
        except Exception as e:
            print(f"ERR running {script_name}: {str(e)[:50]}")
    else:
        print(f"ERR: {script_name} not found")

def fancy_pause(seconds=3):
    for i in range(seconds, 0, -1):
        print(f"⏳ Pausing {i}s", end="\r", flush=True)
        time.sleep(1)
    print(" " * 30, end="\r")

# ---------------- MAIN LOOP ----------------
def main_loop():
    # Run execprtpxy.py once at start
    run_script(EXEC_PRT_FILE)

    was_open = False
    off_done = False
    loop_counter = 1

    while True:
        mkt = is_market_hours()

        # ---- MARKET OPEN ----
        if mkt and not was_open:
            print(f"[{now_ist().strftime('%H:%M:%S')}] MKT OPEN: starting bot")
            send_telegram("Bot started (market open)")
            off_done = False

        # ---- MARKET CLOSE ----
        if not mkt and was_open:
            print(f"[{now_ist().strftime('%H:%M:%S')}] MKT CLOSE: stopping bot")
            send_telegram("Bot stopped (market close)")
            # Run off-market CE/PE check once
            pos_summary = get_position_summary()
            try:
                ce_qty = int(pos_summary[0])
                pe_qty = int(pos_summary[3])
            except:
                ce_qty = pe_qty = 0

            if ce_qty >= 1 and pe_qty >= 1:
                run_script(EXE_EXIT_FILE)
            elif ce_qty == 0 and pe_qty == 0:
                run_script(EXE_ENT_FILE)
            else:
                run_script(EXE_ENT_FILE)
                run_script(EXE_EXIT_FILE)

            # Run end-of-day cleanup
            run_script(EXE_SELF_FILE)
            off_done = True

        # ---- RUN MARKET LOGIC ----
        if mkt:
            for sub_itr in range(1, 31):
                pos_summary = get_position_summary()
                try:
                    ce_qty = int(pos_summary[0])
                    pe_qty = int(pos_summary[3])
                except:
                    ce_qty = pe_qty = 0

                print(f"[{now_ist().strftime('%H:%M:%S')}] Loop #{loop_counter} | Subloop #{sub_itr} | CE:{ce_qty} PE:{pe_qty}", end="\r")

                if ce_qty >= 1 and pe_qty >= 1:
                    run_script(EXE_EXIT_FILE)
                elif ce_qty == 0 and pe_qty == 0:
                    run_script(EXE_ENT_FILE)
                else:
                    run_script(EXE_ENT_FILE)
                    run_script(EXE_EXIT_FILE)

                fancy_pause(3)
            loop_counter += 1
        else:
            if not off_done:
                # Extra safety off-market check (if market close missed)
                pos_summary = get_position_summary()
                try:
                    ce_qty = int(pos_summary[0])
                    pe_qty = int(pos_summary[3])
                except:
                    ce_qty = pe_qty = 0

                if ce_qty >= 1 and pe_qty >= 1:
                    run_script(EXE_EXIT_FILE)
                elif ce_qty == 0 and pe_qty == 0:
                    run_script(EXE_ENT_FILE)
                else:
                    run_script(EXE_ENT_FILE)
                    run_script(EXE_EXIT_FILE)

                # Run end-of-day cleanup
                run_script(EXE_SELF_FILE)
                off_done = True

            print(f"[{now_ist().strftime('%H:%M:%S')}] Waiting for market open...", end="\r")
            time.sleep(60)

        was_open = mkt
        time.sleep(1)

# ---------------- ENTRY ----------------
if __name__ == "__main__":
    main_loop()
