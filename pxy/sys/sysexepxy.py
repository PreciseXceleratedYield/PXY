#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from datetime import datetime, time as dt_time
import pytz
from syscnfgpxy import RUNMODE
from sysmodepxy import dispatch_mode

# Override RUNMODE from environment if set
RUNTIME_MODE = os.environ.get("RUNMODE", RUNMODE)

# ================================================================================
# STRICT MODE ENFORCEMENT - REFUSE TO START IF NOT PRD
# ================================================================================
def validate_startup_mode():
    """Validate that startup is PRD mode. Refuse CHK/SIM with helpful message."""
    if RUNTIME_MODE == "SIM":
        print("\n" + "="*80)
        print("❌ ENGINE STARTUP BLOCKED: RUNMODE=SIM (Simulation/Backtest Mode)")
        print("="*80)
        print("\nTo run historical backtest/replay:")
        print("  export RUNMODE=SIM")
        print("  python sysexepxy.py")
        print("\nOr use the direct backtest entry point:")
        print("  python run_backtest.py")
        print("="*80 + "\n")
        return False
    
    if RUNTIME_MODE == "CHK":
        print("\n" + "="*80)
        print("❌ ENGINE STARTUP BLOCKED: RUNMODE=CHK (Check/Mock Mode)")
        print("="*80)
        print("\nCheck mode is for testing only. To run in check mode:")
        print("  export RUNMODE=CHK")
        print("  python sysexepxy.py")
        print("\nFor production (live engine), use:")
        print("  export RUNMODE=PRD  (or leave unset)")
        print("  python sysexepxy.py")
        print("="*80 + "\n")
        return False
    
    if RUNTIME_MODE != "PRD":
        print("\n" + "="*80)
        print(f"❌ ENGINE STARTUP BLOCKED: Unknown RUNMODE={RUNTIME_MODE!r}")
        print("="*80)
        print("\nValid modes are:")
        print("  PRD - Production/Live Engine (default)")
        print("  CHK - Check/Mock Mode (testing only)")
        print("  SIM - Simulation/Backtest Mode")
        print("\nSet mode with:")
        print("  export RUNMODE=PRD")
        print("  python sysexepxy.py")
        print("="*80 + "\n")
        return False
    
    return True

# ================================================================================
# MAIN ENGINE STARTUP
# ================================================================================

# Validate mode before proceeding
if not validate_startup_mode():
    sys.exit(1)

# If we reach here, RUNTIME_MODE == "PRD" - safe to continue

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

def _is_market_hours_production():
    """Check if current time is within market hours"""
    now_dt = now_ist()
    t = now_dt.time()
    wd = now_dt.weekday()
    return 0 <= wd <= 4 and MARKET_OPEN <= t < MARKET_CLOSE


def is_market_hours():
    return dispatch_mode("engine_window_open", _is_market_hours_production)

# ---------------- SUPERVISOR LOOP ----------------
def start_loop():
    """Main loop to supervise execution"""
    # PRD mode: normal supervised loop with market hour restrictions
    if dispatch_mode("run_startup_checks", lambda: True):
        run_execprt()
    else:
        print("CHK MODE: startup task paused during market hours.")
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
        time.sleep(max(0, 1 - (time.time() - t0)))  # ~1s loop

# ---------------- ENTRY POINT ----------------
if __name__ == "__main__":
    start_loop()
