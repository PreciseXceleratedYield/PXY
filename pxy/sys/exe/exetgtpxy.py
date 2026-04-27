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
        # 1. DATA
        entry = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry <= 0: return 0
        
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        entry_sig = str(row.get("entry", "NONE")).upper()
        exit_sig = str(row.get("exit", "NONE")).upper()
        atr = f(row.get("atr", 0))
        
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # --- TIME CHECK (IST) ---
        now = datetime.datetime.now(pytz.timezone("Asia/Kolkata")).time()
        is_morning = time(9, 15) <= now < time(9, 30)

        # 2. SIGNAL SELECTION
        # Morning: Use Exit Signal | After 9:30: Use Entry Signal
        sig = exit_sig if is_morning else entry_sig

        # 3. SURGICAL REVERSAL EXIT (TARGET 0 - ACTIVE ONLY AFTER 9:30)
        if not is_morning:
            if (is_ce and entry_sig == "STSELL") or (is_pe and entry_sig == "STBUY"):
                print(f"{symbol}|| 🛑 REVERSAL EXIT || T:0")
                return 0

        # 4. ALIGNMENT
        bullish = any(x in sig for x in ["BUY", "BULL", "UP", "STBUY"])
        bearish = any(x in sig for x in ["SELL", "BEAR", "DOWN", "STSELL"])
        aligned = (is_ce and bullish) or (is_pe and bearish)

        # 5. SCORE & TARGET
        score = max(min(atr, 33), 3) if aligned else 1
        state = "✅" if aligned else "❌"
        
        target = int(entry * (1 + score / 100))
        
        # 6. OUTPUT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        mode = "🌅MORNING" if is_morning else "🕒FULL"
        print(f"{clean_symbol}|| {mode}|| E:{entry:03d}|| S:{int(score):02d}%|| {state} || T:{target:03d}")
        
        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0

