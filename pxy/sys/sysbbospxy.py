from colorama import Fore, Style, init
init(autoreset=True)

# ==================================================
# GLOBAL SETTINGS
# ==================================================
STRUCTURE_WINDOW = 14
DEBUG = False


# ==================================================
# LOGGER
# ==================================================
def log(tag, msg):
    if DEBUG:
        print(f"{Fore.CYAN}[{tag}] {msg}{Style.RESET_ALL}")


# ==================================================
# STRUCTURE
# ==================================================
def get_structure(df):
    base = df.iloc[-(STRUCTURE_WINDOW + 1):-1]
    high = base['High'].max()
    low = base['Low'].min()
    return high, low


# ==================================================
# SWEEP DETECTION
# ==================================================
def detect_sweep(df, structure_high, structure_low):
    last = df.iloc[-1]

    if last['High'] > structure_high and last['Close'] < structure_high:
        return "SELL"

    if last['Low'] < structure_low and last['Close'] > structure_low:
        return "BUY"

    return None


# ==================================================
# 🔵 BOS ENGINE (EVENT ONLY)
# ==================================================
def get_bos(df):

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 2:
            return "NONE"

        last = df.iloc[-1]
        prev = df.iloc[-2]

        structure_high, structure_low = get_structure(df)

        log("BOS", f"H:{structure_high} L:{structure_low}")

        # ==================================================
        # 🚀 EVENT SIGNALS ONLY
        # ==================================================
        sweep = detect_sweep(df, structure_high, structure_low)

        if sweep == "BUY":
            return "BUY"

        if sweep == "SELL":
            return "SELL"

        if prev['Close'] <= structure_high and last['Close'] > structure_high:
            return "BUY"

        if prev['Close'] >= structure_low and last['Close'] < structure_low:
            return "SELL"

        # ==================================================
        # ❌ NO TRADE OTHERWISE
        # ==================================================
        return "NONE"

    except Exception:
        return "NONE"


# ==================================================
# ⚙️ SIGNAL ENGINE
# ==================================================
def get_signal(df):
    return get_bos(df)


# ==================================================
# 📊 VISUAL OUTPUT
# ==================================================
def get_bos_bar(df):

    signal = get_signal(df)

    state = "BREAK OUT" if signal in ["BUY", "SELL"] else "NO TRADE"

    banner = "     ﮩ٨ﮩ٨ـﮩ٨ـﮩﮩ٨ﮩ_" + state + "_٨ـﮩ٨ـ٨ﮩ٨ـﮩﮩﮩﮩ"

    if signal == "BUY":
        return Fore.GREEN + banner + Style.RESET_ALL, signal

    if signal == "SELL":
        return Fore.RED + banner + Style.RESET_ALL, signal

    return Fore.LIGHTBLACK_EX + banner + Style.RESET_ALL, signal
