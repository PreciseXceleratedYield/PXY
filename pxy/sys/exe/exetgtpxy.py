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
        ce_power = f(row.get("ce_power", 0))
        pe_power = f(row.get("pe_power", 0))

        # 3️⃣ OPTION TYPE
        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        # 4️⃣ SIGNAL (keep your existing structure)
        entry_signal = str(row.get("entry", "NONE")).upper()
        exit_signal = str(row.get("exit", "NONE")).upper()
        direction_signal = str(row.get("direction", "NONE")).upper()
        counter = str(row.get("counter", "Y")).upper()

        _signal = exit_signal if counter == "Y" else direction_signal

        bullish = any(x in _signal for x in ["BUY", "BULL", "UP"])
        bearish = any(x in _signal for x in ["SELL", "BEAR", "DOWN"])

        # 5️⃣ ALIGNMENT
        aligned = (
            (is_ce and bullish) or
            (is_pe and bearish)
        )

        # 6️⃣ SCORE → ATR × RELEVANT POWER
        if aligned:
            power = ce_power if is_ce else pe_power if is_pe else 0

            score = atr * power

            # safety controls
            score = max(score, 1)
            score = min(score, 50)

            state = "✅"
        else:
            score = 1
            state = "❌"

        # 7️⃣ TARGET
        target = int(entry * (1 + score / 100))

        # 8️⃣ CLEAN SYMBOL
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 9️⃣ OUTPUT
        print(f"{clean_symbol}|| E:{entry:03d}|| S:{int(score):02d}%|| {state} || T:{target:03d}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0
