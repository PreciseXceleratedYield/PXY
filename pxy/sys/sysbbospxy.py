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
# SWEEP DETECTION (UNCHANGED BUT NOT USED FOR DIRECTION NOW)
# ==================================================
def detect_sweep(df, structure_high, structure_low):
    last = df.iloc[-1]

    if last['High'] > structure_high and last['Close'] < structure_high:
        return "SELL"

    if last['Low'] < structure_low and last['Close'] > structure_low:
        return "BUY"

    return None


# ==================================================
# 🔵 BOS ENGINE (ONLY STRUCTURE DIRECTION)
# ==================================================
def get_bos(df):

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 2:
            return "SIDE"

        log("BOS", "calculating structure direction")

        # ==================================================
        # 🔥 STRUCTURE DIRECTION ONLY
        # ==================================================
        prev_high = df['High'].iloc[-15:-1].max()
        prev_low  = df['Low'].iloc[-15:-1].min()

        curr_high = df['High'].iloc[-14:].max()
        curr_low  = df['Low'].iloc[-14:].min()

        if curr_high > prev_high and curr_low >= prev_low:
            return "BULL"

        if curr_high <= prev_high and curr_low < prev_low:
            return "BEAR"

        return "SIDE"

    except Exception:
        return "SIDE"


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

    state = signal  # BULL / BEAR / SIDE

    banner = "     ﮩ٨ﮩ٨ـﮩ٨ـﮩﮩ٨ﮩ_" + state + "_٨ـﮩ٨ـ٨ﮩ٨ـﮩﮩﮩﮩ"

    if signal == "BULL":
        return Fore.GREEN + banner + Style.RESET_ALL, signal

    if signal == "BEAR":
        return Fore.RED + banner + Style.RESET_ALL, signal

    return Fore.LIGHTBLACK_EX + banner + Style.RESET_ALL, signal
