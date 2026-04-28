# sys/exe/exetgtpxy_dashboard.py
from datetime import time
import datetime
import pytz
from colorama import init

init(autoreset=True)

def i(x, d=0):
    try: return int(float(x))
    except: return d

def target_price(row):
    try:
        # 1. DATA FETCH
        entry = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry <= 0: return 0

        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        # sig = st_signal from your ST script (BUY, SELL, UP, DOWN)
        sig = str(row.get("entry", "NONE")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # --- TIME CHECK (IST) ---
        now = datetime.datetime.now(pytz.timezone("Asia/Kolkata")).time()
        is_morning = time(9, 15) <= now < time(9, 30)

        # 2. 🚨 THE MASTER KILL-SWITCH (STRICT)
        if not is_morning:
            # While SELL or DOWN: Kill CE
            if is_ce and any(x in sig for x in ["SELL", "DOWN"]):
                print(f"{symbol}|| 🛑 TREND_IS_DOWN || KILL_CE || T:0")
                return 0
            # While BUY or UP: Kill PE
            if is_pe and any(x in sig for x in ["BUY", "UP"]):
                print(f"{symbol}|| 🛑 TREND_IS_UP || KILL_PE || T:0")
                return 0

        # 3. 🎯 DYNAMIC TARGET LOGIC (RELAXED HOLD)
        # As long as the "Gate" above didn't kill it, we calculate targets
        
        if is_ce:
            if "BUY" in sig:
                score = 20.0  # Strong Bullish Trigger
                state = "🔥"
            else:
                score = 1.4   # Steady Bullish Flow (UP)
                state = "✅"
        
        elif is_pe:
            if "SELL" in sig:
                score = 20.0  # Strong Bearish Trigger
                state = "🔥"
            else:
                score = 1.4   # Steady Bearish Flow (DOWN)
                state = "✅"
        
        else:
            score = 1.4
            state = "⚪"

        target = int(entry * (1 + score / 100))

        # 4. OUTPUT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        print(f"{clean_symbol}|| E:{entry:03d}|| S:{score:.1f}%|| {state} || T:{target:03d}")
        
        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0




