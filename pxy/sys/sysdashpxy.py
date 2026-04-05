# sysdashpxy.py

import runpy
import os
from colorama import Fore, Style, init

init(autoreset=True)

# ---- Imports ----
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_ha_data
from syshkinpxy import detect_ha_flip_signal
from sysstrhpxy import get_candle_strength_line
from syskatrpxy import calculate_atr, calculate_dynamic_k
from sysexitpxy import detect_raw_direction
from sysstrndpxy import calculate_supertrend
from syspwerpxy import get_ce_pe_power
from sysentrpxy import get_entry_signal
from sysdeptpxy import get_candle_visual
from syscndlpxy import get_day_candle_bar
from sysbbospxy import get_bos_bar

TOTAL_WIDTH = 42

# ================= RUN PYC =================
def run_pyc_file():
    pyc_files = []

    for pyc_file in pyc_files:
        try:
            runpy.run_path(os.path.join(os.getcwd(), pyc_file), run_name="__main__")
        except Exception as e:
            print(f"Error running {pyc_file}: {e}")

# ================= CORE SNAPSHOT FUNCTION =================
def get_full_snapshot():
    result = {}

    # ================= FETCH =================
    df = fetch_yf_data()
    if df is None or df.empty:
        return None

    result["df"] = df

    # ================= CANDLE VISUAL =================
    result["candle_visual"] = get_candle_visual(df=df)

    # ================= HA =================
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)
    result["ha_close"] = ha_close
    result["ha_open"] = ha_open
    result["ha_color"] = ha_color

    # ================= HAIKIN SIGNAL =================
    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal(df=df)
    result["hkin_signal"] = signal
    result["hkin_past_depth"] = past_depth
    result["hkin_ce_depth"] = ce_depth
    result["hkin_pe_depth"] = pe_depth

    # ================= STRENGTH =================
    line, _, _ = get_candle_strength_line(df=df)
    result["strength_line"] = line

    # ================= ATR =================
    atr_series = calculate_atr(df)
    atr_val = int(atr_series.iloc[-1]) if not atr_series.empty else 0
    k_val = calculate_dynamic_k(df)

    result["atr"] = atr_val
    result["katr"] = k_val

    # ================= PRICE =================
    price, direction = detect_raw_direction(df)
    result["price"] = int(price) if price else None
    result["direction"] = direction

    # ================= SUPERTREND =================
    df = calculate_supertrend(df)
    trend = df['ST_Trend'].iloc[-1]
    line_val = int(df['ST'].iloc[-1])

    result["supertrend"] = trend
    result["super_line"] = line_val
    result["df"] = df  # updated df

    # ================= POWER =================
    direction_power, ce, pe = get_ce_pe_power(df=df)

    result["direction_power"] = direction_power
    result["ce_power"] = ce
    result["pe_power"] = pe

    # ================= ENTRY =================
    entry, reversal = get_entry_signal(df)
    result["entry"] = entry
    result["reversal"] = reversal

    # ================= DAY CANDLE =================
    result["day_candle"] = get_day_candle_bar(df)

    # ================= BOS =================
    bos_bar, bos_val = get_bos_bar(df)
    result["bos_bar"] = bos_bar
    result["bos_val"] = bos_val

    # ================= CHART DATA (CRITICAL) =================
    try:
        last_idx = df.index[-1]
    
        # Case 1: DatetimeIndex
        if hasattr(last_idx, "timestamp"):
            ts = int(last_idx.timestamp())
    
        # Case 2: fallback → use current time
        else:
            from datetime import datetime
            import pytz
            ist = pytz.timezone("Asia/Kolkata")
            ts = int(datetime.now(ist).timestamp())
    
    except Exception:
        from datetime import datetime
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        ts = int(datetime.now(ist).timestamp())
    
    result["timestamp"] = ts
    result["close"] = float(df["Close"].iloc[-1])

    return result

# ================= PRINT DASHBOARD =================
def print_dashboard(data):
    if not data:
        print("No data fetched.")
        return

    df = data["df"]

    # ================= CANDLE =================
    print(data["candle_visual"])

    # ================= HAIKIN =================
    signal = data["hkin_signal"]
    past_depth = data["hkin_past_depth"]
    ce_depth = data["hkin_ce_depth"]
    pe_depth = data["hkin_pe_depth"]

    color = Fore.GREEN if signal in ["BUY","BULL"] else Fore.RED if signal in ["SELL","BEAR"] else Fore.YELLOW

    space1 = TOTAL_WIDTH - len(f"Hkin:{signal}") - len(f"Past:{past_depth}")
    if space1 < 0: space1 = 1
    print(Fore.YELLOW + "Hkin:" + color + signal + " " * space1 + Fore.YELLOW + f"Past:{color}{past_depth}")

    space2 = TOTAL_WIDTH - len(f"CE:{ce_depth}") - len(f"PE:{pe_depth}")
    if space2 < 0: space2 = 1
    print(Fore.YELLOW + "CE:" + color + str(ce_depth) + " " * space2 + Fore.YELLOW + "PE:" + color + str(pe_depth))

    # ================= STRENGTH =================
    print(data["strength_line"])

    # ================= ATR =================
    atr_val = data["atr"]
    k_val = data["katr"]
    space = TOTAL_WIDTH - len(f"ATR:{atr_val}") - len(f"KATR:{k_val}")
    print(Fore.YELLOW + "ATR:" + Fore.WHITE + str(atr_val) + " " * space + Fore.YELLOW + "KATR:" + Fore.CYAN + str(k_val))

    # ================= PRICE =================
    price = data["price"]
    direction = data["direction"]
    color = Fore.GREEN if direction=="UP" else Fore.RED if direction=="DOWN" else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Price:{price}") - len(f"Mullu:{direction}")
    print(Fore.YELLOW + "Price:" + color + str(price) + " " * space + Fore.YELLOW + "Mullu:" + color + direction)

    # ================= SUPERTREND =================
    trend = data["supertrend"]
    line_val = data["super_line"]
    color = Fore.GREEN if trend=="UP" else Fore.RED if trend=="DOWN" else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Super:{trend}") - len(f"LINE:{line_val}")
    print(Fore.YELLOW + "Super:" + color + trend + " " * space + Fore.YELLOW + "LINE:" + color + str(line_val))

    # ================= POWER =================
    ce = data["ce_power"]
    pe = data["pe_power"]
    ce_color = Fore.GREEN if ce > pe else Fore.RED if ce < pe else Fore.YELLOW
    pe_color = Fore.GREEN if pe > ce else Fore.RED if pe < ce else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"CE Power:{ce}") - len(f"PE Power:{pe}")
    print(Fore.YELLOW + "CE Power:" + ce_color + str(ce) + " " * space + Fore.YELLOW + "PE Power:" + pe_color + str(pe))

    # ================= ENTRY =================
    entry = data["entry"]
    reversal = data["reversal"]
    color = Fore.GREEN if entry in ["BUY","BULL"] else Fore.RED if entry in ["SELL","BEAR"] else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Entry:{entry}") - len(f"Rvrsl:{reversal}")
    print(Fore.YELLOW + "Entry:" + color + entry + " " * space + Fore.YELLOW + "Rvrsl:" + color + reversal)

    # ================= BOS BAR =================
    print(data["bos_bar"])

# ================= MAIN =================
if __name__ == "__main__":
    run_pyc_file()
    data = get_full_snapshot()
    print_dashboard(data)
