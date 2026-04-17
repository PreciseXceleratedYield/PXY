from colorama import Fore, Style, init
init(autoreset=True)

# ==================================================
# GLOBAL SETTINGS
# ==================================================
MODE = "HKIN"      # "BOS" or "HKIN"
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
# 🔵 YOUR ORIGINAL BOS CODE (UNCHANGED)
# ==================================================
# 👉 KEEP YOUR EXISTING get_structure / detect_sweep / get_bos EXACTLY AS IS
# 👉 PASTED HERE AS PLACEHOLDER

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

        log("BOS", f"High={structure_high:.2f} Low={structure_low:.2f}")

        sweep_signal = detect_sweep(df, structure_high, structure_low)

        if sweep_signal == "SWEEP_BUY":
            log("BOS", "SWEEP BUY")
            return "BUY"

        if sweep_signal == "SWEEP_SELL":
            log("BOS", "SWEEP SELL")
            return "SELL"

        if prev['Close'] <= structure_high and last['Close'] > structure_high:
            log("BOS", "BREAK HIGH → BUY")
            return "BUY"

        if prev['Close'] >= structure_low and last['Close'] < structure_low:
            log("BOS", "BREAK LOW → SELL")
            return "SELL"

        if last['Close'] > structure_high:
            return "UP"

        if last['Close'] < structure_low:
            return "DOWN"

        return "UP" if last['Close'] >= mid else "DOWN"

    except Exception as e:
        log("BOS_ERROR", str(e))
        return "NONE"


# ==================================================
# ==================================================
# 🟢 HKIN (PARALLEL ENGINE)
# ==================================================
_prev_hkin_state = None


def get_hkin_state(df):

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

    except Exception as e:
        log("HKIN_ERROR", str(e))
        return "NONE"


def get_hkin_signal(df):

    global _prev_hkin_state

    current = get_hkin_state(df)

    signal = "NONE"

    log("HKIN", f"Prev={_prev_hkin_state} Current={current}")

    if _prev_hkin_state == "DOWN" and current == "UP":
        signal = "BUY"
        log("HKIN", "FLIP → BUY")

    elif _prev_hkin_state == "UP" and current == "DOWN":
        signal = "SELL"
        log("HKIN", "FLIP → SELL")

    else:
        signal = current

    _prev_hkin_state = current

    return signal


# ==================================================
# ==================================================
# ⚙️ UNIFIED SWITCH ENGINE
# ==================================================
def get_signal(df):

    log("MODE", MODE)

    if MODE == "HKIN":
        return get_hkin_signal(df)

    return get_bos(df)


# ==================================================
# ==================================================
# 📊 VISUAL BAR (SAME STYLE FOR BOTH)
# ==================================================
def get_bos_bar(df):

    signal = get_signal(df)

    log("SIGNAL", signal)

    if signal == "BUY":
        return Fore.GREEN + "█" * 42 + Style.RESET_ALL, signal

    if signal == "SELL":
        return Fore.RED + "█" * 42 + Style.RESET_ALL, signal

    if signal == "UP":
        return Fore.GREEN + "█" * 42 + Style.RESET_ALL, signal

    if signal == "DOWN":
        return Fore.RED + "█" * 42 + Style.RESET_ALL, signal

    return Fore.LIGHTBLACK_EX + "░" * 42 + Style.RESET_ALL, signal
