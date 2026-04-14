# run_pyc.py
import runpy
import os
import time
import yfinance as yf   # ✅ self-fetch
from colorama import Fore, Style, init

init(autoreset=True)

# ---- Imports ----
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

# ================= FETCH (SELF DEPENDENT) =================
def fetch_yf_data(symbol):
    try:
        ticker = yf.Ticker(symbol)

        # ✅ Try 1: 1 day / 1 min
        df = ticker.history(interval="1m", period="1d")

        # 🔁 fallback: 5 day / 1 min
        if df is None or df.empty:
            df = ticker.history(interval="1m", period="5d")

        # 🔁 final fallback (optional safety)
        if df is None or df.empty:
            df = ticker.history(interval="5m", period="5d")

        if df is None or df.empty:
            print(f"❌ No data for {symbol}")
            return None

        return df

    except Exception as e:
        print(f"YF Error ({symbol}):", e)
        return None

# ---------------- UTILS ----------------
def safe_int(val):
    try:
        return 0 if val is None else int(float(val))
    except (ValueError, TypeError):
        return 0

# ================= RUN PYC FILES =================
def run_pyc_file():
    pyc_files = []
    for pyc_file in pyc_files:
        try:
            runpy.run_path(os.path.join(os.getcwd(), pyc_file), run_name="__main__")
        except Exception as e:
            print(f"Error running {pyc_file}: {e}")

# ================= CORE SNAPSHOT FUNCTION =================
def get_full_snapshot(symbol):
    result = {}

    df = fetch_yf_data(symbol)
    if df is None or df.empty:
        return None
    result["df"] = df

    result["candle_visual"] = get_candle_visual(df=df)

    # ===== HAIKIN-ASHI =====
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)
    result["ha_close"] = ha_close
    result["ha_open"] = ha_open
    result["ha_color"] = ha_color

    # ===== HAIKIN SIGNAL =====
    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal(df=df)
    if signal is None:
        signal = "BULL" if df['HA_Close'].iloc[-1] > df['HA_Open'].iloc[-1] else "BEAR"
    result["hkin_signal"] = signal
    result["hkin_past_depth"] = past_depth
    result["hkin_ce_depth"] = ce_depth
    result["hkin_pe_depth"] = pe_depth

    # ===== STRENGTH =====
    line, _, _ = get_candle_strength_line(df=df)
    result["strength_line"] = line

    # ===== ATR & KATR =====
    atr_series = calculate_atr(df)
    atr_val = safe_int(atr_series.iloc[-1] if not atr_series.empty else 0)
    k_val = safe_int(calculate_dynamic_k(df))
    result["atr"] = atr_val
    result["katr"] = k_val

    # ===== PRICE =====
    price, direction = detect_raw_direction(df)
    result["price"] = safe_int(price)
    result["direction"] = direction if direction else "NONE"

    # ===== SUPERTREND =====
    df = calculate_supertrend(df)
    trend = df['ST_Trend'].iloc[-1] if not df.empty else "NONE"
    line_val = safe_int(df['ST'].iloc[-1] if not df.empty else 0)
    result["supertrend"] = trend
    result["super_line"] = line_val
    result["df"] = df

    # ===== POWER =====
    direction_power, ce, pe = get_ce_pe_power(df=df)
    result["direction_power"] = safe_int(direction_power)
    result["ce_power"] = safe_int(ce)
    result["pe_power"] = safe_int(pe)

    # ===== ENTRY SIGNAL =====
    entry, reversal = get_entry_signal(df)
    if entry is None or entry == "NONE":
        last_close = df['Close'].iloc[-1]
        st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last_close
        if last_close > st_value:
            entry = "ATMBUY"
            reversal = "SBUY"
        else:
            entry = "ATMSELL"
            reversal = "SSELL"
    result["entry"] = entry
    result["reversal"] = reversal

    # ===== DAY CANDLE =====
    result["day_candle"] = get_day_candle_bar(df)

    # ===== BOS =====
    bos_bar, bos_val = get_bos_bar(df)
    result["bos_bar"] = bos_bar if bos_bar else "NONE"
    result["bos_val"] = bos_val if bos_val else "NONE"

    return result

# ================= PRINT DASHBOARD =================
def print_dashboard(data):
    if not data:
        print("No data fetched.")
        return

    print(data["candle_visual"])

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

    print(data["strength_line"])

    atr_val = data["atr"]
    k_val = data["katr"]
    space = TOTAL_WIDTH - len(f"ATR:{atr_val}") - len(f"KATR:{k_val}")
    print(Fore.YELLOW + "ATR:" + Fore.WHITE + str(atr_val) + " " * space + Fore.YELLOW + "KATR:" + Fore.CYAN + str(k_val))

    price = data["price"]
    direction = data["direction"]
    color = Fore.GREEN if direction=="UP" else Fore.RED if direction=="DOWN" else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Price:{price}") - len(f"Mullu:{direction}")
    print(Fore.YELLOW + "Price:" + color + str(price) + " " * space + Fore.YELLOW + "Mullu:" + color + direction)

    trend = data["supertrend"]
    line_val = data["super_line"]
    color = Fore.GREEN if trend=="UP" else Fore.RED if trend=="DOWN" else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Super:{trend}") - len(f"LINE:{line_val}")
    print(Fore.YELLOW + "Super:" + color + trend + " " * space + Fore.YELLOW + "LINE:" + color + str(line_val))

    ce = data["ce_power"]
    pe = data["pe_power"]
    ce_color = Fore.GREEN if ce > pe else Fore.RED if ce < pe else Fore.YELLOW
    pe_color = Fore.GREEN if pe > ce else Fore.RED if pe < ce else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"CE Power:{ce}") - len(f"PE Power:{pe}")
    print(Fore.YELLOW + "CE Power:" + ce_color + str(ce) + " " * space + Fore.YELLOW + "PE Power:" + pe_color + str(pe))

    entry = data["entry"]
    reversal = data["reversal"]
    color = (
        Fore.GREEN if entry in ["ATMBUY","OTMBUY","SBUY","BBUY","RBUY"] 
        else Fore.RED if entry in ["ATMSELL","OTMSELL","SSELL","BSELL","RSELL"] 
        else Fore.YELLOW
    )
    space = TOTAL_WIDTH - len(f"Entry:{entry}") - len(f"Signal:{reversal}")
    print(Fore.YELLOW + "Entry:" + color + entry + " " * space + Fore.YELLOW + "Signal:" + color + reversal)

    print(data["bos_bar"])

# ================= MAIN LOOP =================
if __name__ == "__main__":
    symbol = input("Enter Symbol: ").strip()   # ✅ ask once

    while True:
        run_pyc_file()
        data = get_full_snapshot(symbol)
        print_dashboard(data)
        time.sleep(6)
