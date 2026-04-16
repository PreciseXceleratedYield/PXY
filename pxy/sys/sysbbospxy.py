from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_WINDOW = 14
MAX_BAR_LENGTH = 42


def get_bos(df):
    """
    BOS Hybrid (CLEAN + STATELSS):

    - BUY / SELL → only on fresh breakout candle
    - UP / DOWN → trend inside structure
    - no memory, no repeats, no noise loops
    """

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 2:
            return "NONE"

        data = df.copy()

        last_close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]

        # ==================================================
        # CLEAN STRUCTURE ZONE (FIXED, NO DRIFT)
        # ==================================================
        base = data.iloc[-STRUCTURE_WINDOW:]

        structure_high = base['High'].max()
        structure_low = base['Low'].min()

        mid = (structure_high + structure_low) / 2

        # small buffer to avoid fake wicks
        buffer = (structure_high - structure_low) * 0.01

        # ==================================================
        # STEP 1: STRICT FIRST BREAKOUT (ONLY ONCE PER EVENT)
        # ==================================================

        # 🟢 BUY breakout
        if prev_close <= structure_high and last_close > structure_high + buffer:
            return "BUY"

        # 🔴 SELL breakout
        if prev_close >= structure_low and last_close < structure_low - buffer:
            return "SELL"

        # ==================================================
        # STEP 2: CONTINUATION TREND
        # ==================================================
        if last_close > structure_high:
            return "UP"

        if last_close < structure_low:
            return "DOWN"

        return "UP" if last_close >= mid else "DOWN"

    except Exception:
        return "NONE"


# ==================================================
# VISUAL BAR (UNCHANGED)
# ==================================================
def get_bos_bar(df):

    try:
        signal = get_bos(df)

        if signal == "NONE":
            bar = Fore.LIGHTBLACK_EX + "░" * MAX_BAR_LENGTH
            return bar + Style.RESET_ALL, signal

        left_len = MAX_BAR_LENGTH // 2
        right_len = MAX_BAR_LENGTH - left_len

        if signal == "BUY":
            bar = Fore.GREEN + "█" * MAX_BAR_LENGTH

        elif signal == "SELL":
            bar = Fore.RED + "█" * MAX_BAR_LENGTH

        elif signal == "UP":
            bar = Fore.LIGHTBLACK_EX + "█" * left_len
            bar += Fore.GREEN + "█" * right_len

        else:  # DOWN
            bar = Fore.RED + "█" * left_len
            bar += Fore.LIGHTBLACK_EX + "█" * right_len

        return bar + Style.RESET_ALL, signal

    except Exception as e:
        return f"ERR: {e}", "ERR"
