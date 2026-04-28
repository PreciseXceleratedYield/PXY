# sys/exe/exetgtpxy_dashboard.py
from datetime import time
import datetime
import pytz
from colorama import init

# Initialize colorama for clean console output
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
        if entry <= 0: 
            return 0

        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        # sig matches st_signal from your SuperTrend script (BUY, SELL, UP, DOWN)
        sig = str(row.get("entry", "NONE")).upper()
        exit_sig = str(row.get("exit", "NONE")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # --- TIME CHECK (IST) ---
        now = datetime.datetime.now(pytz.timezone("Asia/Kolkata")).time()
        is_morning = time(9, 15) <= now < time(9, 30)

        # 2. 🚨 THE MASTER SUPERTREND GATE (STRICT)
        # This ensures CE and PE never exist at the same time post 9:30
        if not is_morning:
            # If trend is Bearish (DOWN/SELL), kill CE
            if is_ce and any(x in sig for x in ["SELL", "DOWN"]):
                print(f"{symbol}|| 🛑 GATE_CLOSED_DOWN || T:0")
                return 0
            # If trend is Bullish (UP/BUY), kill PE
            if is_pe and any(x in sig for x in ["BUY", "UP"]):
                print(f"{symbol}|| 🛑 GATE_CLOSED_UP || T:0")
                return 0

        # 3. SIGNAL SOURCE
        # Morning uses OC/2 flow, after 9:30 uses the SuperTrend signal
        calc_sig = exit_sig if is_morning else sig

        # 4. ALIGNMENT & RELAXED SCORING
        # "Aligned" means position matches trend direction
        is_bullish = any(x in calc_sig for x in ["BUY", "UP", "BULL"])
        is_bearish = any(x in calc_sig for x in ["SELL", "DOWN", "BEAR"])
        
        aligned = (is_ce and is_bullish) or (is_pe and is_bearish)

        if aligned:
            # Strong Trigger (Fresh BUY/SELL) -> 20%
            if any(x in calc_sig for x in ["BUY", "SELL"]):
                score = 20.0
                state = "🔥"
            # Continuous Flow (UP/DOWN) -> 1.4% (Relaxed)
            else:
                score = 1.4
                state = "✅"
        else:
            # Morning buffer or neutral states
            score = 1.4
            state = "❌"

        # 5. CALCULATION
        target = int(entry * (1 + score / 100))

        # 6. CLEAN OUTPUT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        print(f"{clean_symbol}|| E:{entry:03d}|| S:{score:.1f}%|| {state} || T:{target:03d}")
        
        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0



