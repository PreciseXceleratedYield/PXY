from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_WINDOW = 14
SWEEP_BUFFER = 0.0015  # liquidity sweep sensitivity


# ==================================================
# STRUCTURE ENGINE (NON-REPAINT)
# ==================================================
def get_structure(df):
    base = df.iloc[-(STRUCTURE_WINDOW + 1):-1]

    high = base['High'].max()
    low = base['Low'].min()
    mid = (high + low) / 2

    return high, low, mid


# ==================================================
# LIQUIDITY SWEEP DETECTOR
# ==================================================
def detect_sweep(df, structure_high, structure_low):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # sweep high (fake breakout above resistance)
    sweep_high = (
        last['High'] > structure_high and
        last['Close'] < structure_high
    )

    # sweep low (fake breakdown below support)
    sweep_low = (
        last['Low'] < structure_low and
        last['Close'] > structure_low
    )

    if sweep_high:
        return "SWEEP_SELL"
    if sweep_low:
        return "SWEEP_BUY"

    return None


# ==================================================
# BOS + CHOCH ENGINE (INSTITUTIONAL LOGIC)
# ==================================================
def get_bos(df):

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 2:
            return "NONE"

        last = df.iloc[-1]
        prev = df.iloc[-2]

        structure_high, structure_low, mid = get_structure(df)

        # ==================================================
        # STEP 1: LIQUIDITY SWEEP (HIGHEST PRIORITY)
        # ==================================================
        sweep_signal = detect_sweep(df, structure_high, structure_low)

        if sweep_signal == "SWEEP_BUY":
            return "BUY"

        if sweep_signal == "SWEEP_SELL":
            return "SELL"

        # ==================================================
        # STEP 2: TRUE BREAK OF STRUCTURE (BOS)
        # ==================================================
        if prev['Close'] <= structure_high and last['Close'] > structure_high:
            return "BUY"

        if prev['Close'] >= structure_low and last['Close'] < structure_low:
            return "SELL"

        # ==================================================
        # STEP 3: CHOCH (TREND REVERSAL CONFIRMATION)
        # ==================================================
        if last['Close'] > structure_high:
            return "UP"

        if last['Close'] < structure_low:
            return "DOWN"

        # ==================================================
        # STEP 4: RANGE MODE (NO TRADE ZONE FEEL)
        # ==================================================
        return "UP" if last['Close'] >= mid else "DOWN"

    except Exception:
        return "NONE"


# ==================================================
# VISUAL BAR (IMPROVED SIGNAL MAPPING)
# ==================================================
def get_bos_bar(df):

    try:
        signal = get_bos(df)

        if signal == "NONE":
            return Fore.LIGHTBLACK_EX + "░" * 42 + Style.RESET_ALL, signal

        if signal == "BUY":
            return Fore.GREEN + "█" * 42 + Style.RESET_ALL, signal

        if signal == "SELL":
            return Fore.RED + "█" * 42 + Style.RESET_ALL, signal

        if signal == "UP":
            bar = Fore.LIGHTBLACK_EX + "█" * 21
            bar += Fore.GREEN + "█" * 21
            return bar + Style.RESET_ALL, signal

        if signal == "DOWN":
            bar = Fore.RED + "█" * 21
            bar += Fore.LIGHTBLACK_EX + "█" * 21
            return bar + Style.RESET_ALL, signal

    except Exception as e:
        return f"ERR: {e}", "ERR"
