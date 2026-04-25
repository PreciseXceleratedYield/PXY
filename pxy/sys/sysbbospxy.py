from colorama import Fore, Style, init
init(autoreset=True)

# ==================================================
# GLOBAL SETTINGS
# ==================================================
STRUCTURE_WINDOW = 30
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
# SWEEP DETECTION (NOT USED FOR DIRECTION)
# ==================================================
def detect_sweep(df, structure_high, structure_low):
    last = df.iloc[-1]

    if last['High'] > structure_high and last['Close'] < structure_high:
        return "SELL"

    if last['Low'] < structure_low and last['Close'] > structure_low:
        return "BUY"

    return None


# ==================================================
# 🔵 STRUCTURE DIRECTION ENGINE (30 WINDOW)
# ==================================================
def get_bos(df):

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 2:
            return "SIDE"

        log("BOS", "calculating structure direction")

        # ==================================================
        # 🔥 STRUCTURE LOGIC (30 WINDOW)
        # ==================================================
        prev_high = df['High'].iloc[-(STRUCTURE_WINDOW + 1):-1].max()
        prev_low  = df['Low'].iloc[-(STRUCTURE_WINDOW + 1):-1].min()

        curr_high = df['High'].iloc[-STRUCTURE_WINDOW:].max()
        curr_low  = df['Low'].iloc[-STRUCTURE_WINDOW:].min()

        if curr_high > prev_high and curr_low >= prev_low:
            return "BULL"

        if curr_high <= prev_high and curr_low < prev_low:
            return "BEAR"

        return "SIDE"

    except Exception:
        return "SIDE"


# ==================================================
# SIGNAL ENGINE
# ==================================================
def get_signal(df):
    return get_bos(df)


# ==================================================
# VISUAL OUTPUT
# ==================================================
def get_bos_bar(df):

    signal = get_signal(df)

    state = signal

    banner = "     ﮩ٨ﮩ٨ـﮩ٨ـﮩﮩ٨ﮩ_" + state + "_٨ـﮩ٨ـ٨ﮩ٨ـﮩﮩﮩﮩ"

    if signal == "BULL":
        return Fore.GREEN + banner + Style.RESET_ALL, signal

    if signal == "BEAR":
        return Fore.RED + banner + Style.RESET_ALL, signal

    return Fore.LIGHTBLACK_EX + banner + Style.RESET_ALL, signal
