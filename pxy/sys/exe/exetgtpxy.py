# sys/exe/exetgtpxy_dashboard.py

import math
from colorama import init

init(autoreset=True)

# -------------------- SAFE HELPERS --------------------
def f(x, d=0.0):
    try:
        return float(x)
    except:
        return d


def i(x, d=0):
    try:
        return int(float(x))
    except:
        return d


# -------------------- MAIN ENGINE --------------------
def target_price(row):
    try:
        # 1️⃣ ENTRY
        entry = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry <= 0:
            print("INVALID_ENTRY|SKIP")
            return 0

        symbol = str(row.get("symbol", "UNKNOWN")).upper()

        # 2️⃣ INPUTS
        atr = f(row.get("atr", 0))

        # 3️⃣ MIN POINTS (ATR BASED)
        MIN_POINTS = 2

        # 4️⃣ SIGNAL
        exit_signal = str(row.get("entry", "NONE")).upper()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        bullish = any(x in exit_signal for x in ["BUY", "BULL", "NONE"])
        bearish = any(x in exit_signal for x in ["SELL", "BEAR", "NONE"])

        # 5️⃣ STRICT ALIGNMENT
        aligned = (
            (is_ce and bullish) or
            (is_pe and bearish)
        )

        # 6️⃣ SCORE (FIXED WITH CORRECT DEPTH KEYS)
        if aligned:
            ce_depth = f(row.get("hkin_ce_depth", 0))
            pe_depth = f(row.get("hkin_pe_depth", 0))
            score = max(atr - abs(ce_depth - pe_depth), 1)
            state = "✅"
        else:
            score = MIN_POINTS
            state = "❌"

        # 7️⃣ TARGET
        target = int(entry * (1 + score / 100))

        # 8️⃣ CLEAN SYMBOL
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 9️⃣ OUTPUT
        print(f"{clean_symbol} || E:{entry:03d} || S:{int(score):02d}% || {state}  || T:{target:03d}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0
