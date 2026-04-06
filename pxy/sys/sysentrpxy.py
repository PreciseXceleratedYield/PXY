# run_pyc.py
import runpy
import os
import math
import pandas as pd
from colorama import Fore, Style, init

# ---------------- INIT ----------------
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
    pyc_files = []  # Add any pyc files to run here
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
        # Create empty df to prevent NODAATA
        df = pd.DataFrame(columns=['Open','High','Low','Close'])
    
    result["df"] = df

    # ================= CANDLE VISUAL =================
    result["candle_visual"] = get_candle_visual(df=df)

    # ================= HA =================
    try:
        ha_close, ha_open, ha_color, df = get_ha_data(df=df)
        result["ha_close"] = ha_close
        result["ha_open"] = ha_open
        result["ha_color"] = ha_color
    except Exception:
        result["ha_close"] = result["ha_open"] = result["ha_color"] = []

    # ================= HAIKIN SIGNAL =================
    try:
        signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal(df=df)
        result["hkin_signal"] = signal
        result["hkin_past_depth"] = past_depth
        result["hkin_ce_depth"] = ce_depth
        result["hkin_pe_depth"] = pe_depth
    except Exception:
        result["hkin_signal"] = "NONE"
        result["hkin_past_depth"] = result["hkin_ce_depth"] = result["hkin_pe_depth"] = 0

    # ================= STRENGTH =================
    try:
        line, _, _ = get_candle_strength_line(df=df)
        result["strength_line"] = line
    except Exception:
        result["strength_line"] = ""

    # ================= ATR =================
    try:
        atr_series = calculate_atr(df)
        atr_val = 0
        if not atr_series.empty and pd.notna(atr_series.iloc[-1]):
            atr_val = int(atr_series.iloc[-1])
    except Exception:
        atr_val = 0
    try:
        k_val = calculate_dynamic_k(df)
    except Exception:
        k_val = 0

    result["atr"] = atr_val
    result["katr"] = k_val

    # ================= PRICE =================
    try:
        price, direction = detect_raw_direction(df)
        price = int(price) if price and pd.notna(price) else 0
        if direction not in ["UP","DOWN"]:
            direction = "NONE"
    except Exception:
        price = 0
        direction = "NONE"

    result["price"] = price
    result["direction"] = direction

    # ================= SUPERTREND =================
    try:
        df = calculate_supertrend(df)
        trend = df['ST_Trend'].iloc[-1] if 'ST_Trend' in df.columns else "NONE"
        line_val = int(df['ST'].iloc[-1]) if 'ST' in df.columns and pd.notna(df['ST'].iloc[-1]) else 0
        result["supertrend"] = trend
        result["super_line"] = line_val
        result["df"] = df
    except Exception:
        result["supertrend"] = "NONE"
        result["super_line"] = 0

    # ================= POWER =================
    try:
        direction_power, ce, pe = get_ce_pe_power(df=df)
        if isinstance(direction_power, str) or direction_power is None or math.isnan(direction_power):
            direction_power = 0
        result["direction_power"] = int(direction_power)
        result["ce_power"] = int(ce) if ce and pd.notna(ce) else 0
        result["pe_power"] = int(pe) if pe and pd.notna(pe) else 0
    except Exception:
        result["direction_power"] = result["ce_power"] = result["pe_power"] = 0

    # ================= ENTRY =================
    try:
        entry, reversal = get_entry_signal(df)
    except Exception:
        entry = "NONE"
        reversal = "NONE"

    result["entry"] = entry
    result["reversal"] = reversal

    # ================= DAY CANDLE =================
    try:
        result["day_candle"] = get_day_candle_bar(df)
    except Exception:
        result["day_candle"] = ""

    # ================= BOS =================
    try:
        bos_bar, bos_val = get_bos_bar(df)
        result["bos_bar"] = bos_bar
        result["bos_val"] = bos_val
    except Exception:
        result["bos_bar"] = ""
        result["bos_val"] = ""

    return result

# ================= PRINT DASHBOARD =================
def print_dashboard(data):
    if not data:
        return  # skip instead of printing NODAATA

    df = data["df"]

    # ================= CANDLE =================
    print(data.get("candle_visual",""))

    # ================= HAIKIN =================
    signal = data.get("hkin_signal","NONE")
    past_depth = data.get("hkin_past_depth",0)
    ce_depth = data.get("hkin_ce_depth",0)
    pe_depth = data.get("hkin_pe_depth",0)

    color = Fore.GREEN if signal in ["BUY","BULL"] else Fore.RED if signal in ["SELL","BEAR"] else Fore.YELLOW
    space1 = TOTAL_WIDTH - len(f"Hkin:{signal}") - len(f"Past:{past_depth}")
    if space1 < 0: space1 = 1
    print(Fore.YELLOW + "Hkin:" + color + signal + " " * space1 + Fore.YELLOW + f"Past:{color}{past_depth}")

    space2 = TOTAL_WIDTH - len(f"CE:{ce_depth}") - len(f"PE:{pe_depth}")
    if space2 < 0: space2 = 1
    print(Fore.YELLOW + "CE:" + color + str(ce_depth) + " " * space2 + Fore.YELLOW + "PE:" + color + str(pe_depth))

    # ================= STRENGTH =================
    print(data.get("strength_line",""))

    # ================= ATR =================
    atr_val = data.get("atr",0)
    k_val = data.get("katr",0)
    space = TOTAL_WIDTH - len(f"ATR:{atr_val}") - len(f"KATR:{k_val}")
    print(Fore.YELLOW + "ATR:" + Fore.WHITE + str(atr_val) + " " * space + Fore.YELLOW + "KATR:" + Fore.CYAN + str(k_val))

    # ================= PRICE =================
    price = data.get("price",0)
    direction = data.get("direction","NONE")
    color = Fore.GREEN if direction=="UP" else Fore.RED if direction=="DOWN" else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Price:{price}") - len(f"Mullu:{direction}")
    print(Fore.YELLOW + "Price:" + color + str(price) + " " * space + Fore.YELLOW + "Mullu:" + color + direction)

    # ================= SUPERTREND =================
    trend = data.get("supertrend","NONE")
    line_val = data.get("super_line",0)
    color = Fore.GREEN if trend=="UP" else Fore.RED if trend=="DOWN" else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Super:{trend}") - len(f"LINE:{line_val}")
    print(Fore.YELLOW + "Super:" + color + trend + " " * space + Fore.YELLOW + "LINE:" + color + str(line_val))

    # ================= POWER =================
    ce = data.get("ce_power",0)
    pe = data.get("pe_power",0)
    ce_color = Fore.GREEN if ce > pe else Fore.RED if ce < pe else Fore.YELLOW
    pe_color = Fore.GREEN if pe > ce else Fore.RED if pe < ce else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"CE Power:{ce}") - len(f"PE Power:{pe}")
    print(Fore.YELLOW + "CE Power:" + ce_color + str(ce) + " " * space + Fore.YELLOW + "PE Power:" + pe_color + str(pe))

    # ================= ENTRY =================
    entry = data.get("entry","NONE")
    reversal = data.get("reversal","NONE")
    color = Fore.GREEN if entry in ["BUY","BULL","ATMBUY","OTMBUY"] else Fore.RED if entry in ["SELL","BEAR","ATMSELL","OTMSELL"] else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Entry:{entry}") - len(f"Signal:{reversal}")
    print(Fore.YELLOW + "Entry:" + color + entry + " " * space + Fore.YELLOW + "Signal:" + color + reversal)

    # ================= DAY CANDLE =================
    #print(data.get("day_candle",""))

    # ================= BOS BAR =================
    print(data.get("bos_bar",""))
    # Optional: print BOS value text
    # print("BOS Value:", data.get("bos_val",""))

# ================= MAIN =================
if __name__ == "__main__":
    run_pyc_file()               # run any pyc files
    data = get_full_snapshot()    # capture all indicators
    print_dashboard(data)         # display dashboard
