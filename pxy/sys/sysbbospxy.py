from colorama import Fore, Style, init
init(autoreset=True)

# ==================================================
# GLOBAL SETTINGS
# ==================================================
MODE = "HKA"      # "BOS" or "HKA"
DEBUG = True

HA_WINDOW = 15
STRUCTURE_WINDOW = 14
SWEEP_BUFFER = 0.0015


# ==================================================
# DEBUG LOGGER
# ==================================================
def log(tag, msg):
    if DEBUG:
        print(f"{Fore.CYAN}[{tag}] {msg}{Style.RESET_ALL}")


# ==================================================
# ==================================================
# 🔵 BOS ENGINE (UNCHANGED)
# ==================================================
def get_structure(df):
    base = df.iloc[-(STRUCTURE_WINDOW + 1):-1]
    high = base['High'].max()
    low = base['Low'].min()
    mid = (high + low) / 2
    return high, low, mid


def detect_sweep(df, structure_high, structure_low):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    sweep_high = (last['High'] > structure_high and last['Close'] < structure_high)
    sweep_low = (last['Low'] < structure_low and last['Close'] > structure_low)

    if sweep_high:
        return "SWEEP_SELL"
    if sweep_low:
        return "SWEEP_BUY"

    return None


def get_bos(df):

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 2:
            return "NONE"

        last = df.iloc[-1]
        prev = df.iloc[-2]

        structure_high, structure_low, mid = get_structure(df)

        log("BOS", f"H:{structure_high} L:{structure_low}")

        sweep_signal = detect_sweep(df, structure_high, structure_low)

        if sweep_signal == "SWEEP_BUY":
            return "BUY"

        if sweep_signal == "SWEEP_SELL":
            return "SELL"

        if prev['Close'] <= structure_high and last['Close'] > structure_high:
            return "BUY"

        if prev['Close'] >= structure_low and last['Close'] < structure_low:
            return "SELL"

        if last['Close'] > structure_high:
            return "UP"

        if last['Close'] < structure_low:
            return "DOWN"

        return "UP" if last['Close'] >= mid else "DOWN"

    except Exception:
        return "NONE"


# ==================================================
# ==================================================
# 🟢 HKA ENGINE (UNCHANGED)
# ==================================================
_prev_HKA_state = None


def get_HKA_state(df):

    try:
        if df is None or len(df) < HA_WINDOW:
            return "NONE"

        base = df.iloc[-HA_WINDOW:]

        ha_close = (base['Open'] + base['High'] + base['Low'] + base['Close']) / 4

        ha_open = [(base['Open'].iloc[0] + base['Close'].iloc[0]) / 2]

        for i in range(1, len(base)):
            ha_open.append((ha_open[i-1] + ha_close.iloc[i-1]) / 2)

        o = ha_open[-1]
        c = ha_close.iloc[-1]

        if c > o:
            return "UP"
        if c < o:
            return "DOWN"
        return "NONE"

    except Exception:
        return "NONE"


def get_HKA_signal(df):

    global _prev_HKA_state

    current = get_HKA_state(df)

    signal = "NONE"

    if _prev_HKA_state == "DOWN" and current == "UP":
        signal = "BUY"

    elif _prev_HKA_state == "UP" and current == "DOWN":
        signal = "SELL"

    else:
        signal = current

    _prev_HKA_state = current

    return signal


# ==================================================
# ==================================================
# ⚙️ SWITCH ENGINE
# ==================================================
def get_signal(df):

    log("MODE", MODE)

    if MODE == "HKA":
        return get_HKA_signal(df)

    return get_bos(df)


# ==================================================
# ==================================================
# 📊 VISUAL OUTPUT (ONLY CHANGE HERE)
# ==================================================
def get_bos_bar(df):

    signal = get_signal(df)

    log("SIGNAL", signal)

    # ==================================================
    # EXACT BANNER FORMAT (NO CHANGES)
    # ==================================================
    banner = "٨٨ﮩ٨ﮩ٨ ـﮩ٨ ﮩ٨ـﮩ٨ ـﮩﮩ٨ﮩ" + MODE + "ﮩ٨ـﮩ٨ـﮩ ﮩ٨ﮩ٨ـﮩﮩ ﮩ٨ﮩﮩ ٨ﮩ"

    # ==================================================
    # COLOR ONLY
    # ==================================================
    if signal in ["BUY", "UP"]:
        return Fore.GREEN + banner + Style.RESET_ALL, signal

    if signal in ["SELL", "DOWN"]:
        return Fore.RED + banner + Style.RESET_ALL, signal

    return Fore.LIGHTBLACK_EX + banner + Style.RESET_ALL, signal
    # ==================================================
    # COLOR ONLY
    # ==================================================
    if signal in ["BUY", "UP"]:
        return Fore.GREEN + banner + Style.RESET_ALL, signal

    if signal in ["SELL", "DOWN"]:
        return Fore.RED + banner + Style.RESET_ALL, signal

    return Fore.LIGHTBLACK_EX + banner + Style.RESET_ALL, signal
