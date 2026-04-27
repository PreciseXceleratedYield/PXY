# sys/exe/exetgtpxy_dashboard.py
from datetime import time
import datetime
import pytz
from colorama import init
init(autoreset=True)

def f(x, d=0.0):
    try: return float(x)
    except: return d

def i(x, d=0):
    try: return int(float(x))
    except: return d

def target_price(row):
    try:
        # 1. DATA FETCH
        entry = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry <= 0: return 0
        
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        sig = str(row.get("entry", "NONE")).upper() 
        exit_sig = str(row.get("exit", "NONE")).upper()
        
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # --- TIME CHECK (IST) ---
        now = datetime.datetime.now(pytz.timezone("Asia/Kolkata")).time()
        is_morning = time(9, 15) <= now < time(9, 30)

        # 2. 🚨 THE MASTER KILL-SWITCH (POST 9:30 ONLY)
        # Kill Target ONLY if the Supertrend Major Trend flips against the position
        if not is_morning:
            if is_ce and any(x in sig for x in ["STSELL", "DOWN"]):
                print(f"{symbol}|| 🛑 ST_OPPOSITE_EXIT || T:0")
                return 0
            if is_pe and any(x in sig for x in ["STBUY", "UP"]):
                print(f"{symbol}|| 🛑 ST_OPPOSITE_EXIT || T:0")
                return 0

        # 3. SIGNAL SOURCE
        # Morning: OC/2 Flow | After 9:30: L4 Entry
        calc_sig = exit_sig if is_morning else sig

        # 4. STRICT ALIGNMENT CHECK (TIGHTENED STRING SEARCH)
        # 'BUY' catches STBUY, ATMBUY, OTMBUY, BUY, etc.
        # 'SELL' catches STSELL, ATMSELL, OTMSELL, SELL, etc.
        bullish = any(x in calc_sig for x in ["BUY", "BULL", "UP"])
        bearish = any(x in calc_sig for x in ["SELL", "BEAR", "DOWN"])
        
        aligned = (is_ce and bullish) or (is_pe and bearish)

        # 5. FIXED SCORE LOGIC (20% vs 1.4%)
        score = 20.0 if aligned else 1.4
        state = "✅ALIGNED" if aligned else "❌MISMATCH"
        
        target = int(entry * (1 + score / 100))
        
        # 6. OUTPUT (CLEAN SYMBOL + DASHBOARD)
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        print(f"{clean_symbol}|| E:{entry:03d}|| S:{score:.1f}%|| {state} || T:{target:03d}")
        
        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0




