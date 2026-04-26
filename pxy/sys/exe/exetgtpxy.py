# sys/exe/exetgtpxy_dashboard.py

import math
from datetime import datetime
import pytz
from colorama import init, Fore, Style

init(autoreset=True)

IST = pytz.timezone("Asia/Kolkata")

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
        ce_power = f(row.get("ce_power", 1))
        pe_power = f(row.get("pe_power", 1))
        supertrend = row.get("supertrend", 0)

        # 3️⃣ OPTION TYPE
        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        # 4️⃣ SIGNALS
        entry_signal = str(row.get("entry", "NONE")).upper()
        exit_signal = str(row.get("exit", "NONE")).upper()
        counter = str(row.get("counter", "Y")).upper()

        _signal = entry_signal if counter == "Y" else exit_signal

        # -------------------- HLD MODE --------------------
        if _signal == "NONE":
            score = 6
            target = int(entry * (1 + score / 100))
            state = "HLD"
            color = Style.NORMAL

            clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
            print(f"{color}{clean_symbol}|| E:{entry:03d}|| S:{score:02d}%|| {state} || T:{target:03d}")
            return target

        # -------------------- SIGNAL TYPE --------------------
        bullish = any(x in _signal for x in ["BUY", "BULL", "UP"])
        bearish = any(x in _signal for x in ["SELL", "BEAR", "DOWN"])

        # -------------------- SUPER TREND --------------------
        st = str(supertrend).strip().upper()
        is_up = st == "UP"
        is_down = st == "DOWN"

        # ==================================================
        # 🔥 MORNING WINDOW OVERRIDE (ONLY CHANGE ADDED)
        # ==================================================
        now = datetime.now(IST)
        in_open_window = (now.hour == 9 and 15 <= now.minute <= 30)

        if in_open_window:
            if is_ce and bullish:
                score = 33
                state = "ALN"
                color = Style.BRIGHT + Fore.GREEN

            elif is_pe and bearish:
                score = 33
                state = "ALN"
                color = Style.BRIGHT + Fore.GREEN

            else:
                score = 1
                state = "NLN"
                color = Style.BRIGHT + Fore.RED

            target = int(entry * (1 + score / 100))
            clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

            print(f"{color}{clean_symbol}|| E:{entry:03d}|| S:{score:02d}%|| {state} || T:{target:03d}")
            return target

        # -------------------- ORIGINAL LOGIC (UNCHANGED) --------------------
        all_aligned = (
            (bullish and is_up and is_ce) or
            (bearish and is_down and is_pe)
        )

        if all_aligned:
            if is_ce:
                score = (atr / 4) * ce_power
            elif is_pe:
                score = (atr / 4) * pe_power
            else:
                score = atr
            state = "ALN"
            color = Style.BRIGHT + Fore.GREEN

        else:
            score = (atr / 4)
            state = "NLN"
            color = Style.BRIGHT + Fore.RED

        target = int(entry * (1 + score / 100))

        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        print(f"{color}{clean_symbol}|| E:{entry:03d}|| S:{int(score):02d}%|| {state} || T:{target:03d}")

        return target

    except Exception as e:
        print(f"{Style.BRIGHT + Fore.RED}ERROR|{str(e)}")
        return 0
