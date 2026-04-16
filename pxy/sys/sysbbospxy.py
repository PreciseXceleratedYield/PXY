from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_WINDOW = 14
MAX_BAR_LENGTH = 42


def get_bos(df):
    """
    BOS Hybrid (FINAL):

    - First structure shift → BUY / SELL (ONE candle only)
    - Then continuous → UP / DOWN
    - Stable, no repeat triggers, no noise
    """

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 5:
            return "NONE"

        data = df.iloc[:-1].copy()

        last_close = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2]

        # ----------------------------
        # STEP 1: find last swing anchor
        # ----------------------------
        last_event_index = None

        for i in range(STRUCTURE_WINDOW, len(data)):
            window = data.iloc[i - STRUCTURE_WINDOW:i]

            high = window['High'].max()
            low  = window['Low'].min()
            close = data['Close'].iloc[i]

            if close >= high or close <= low:
                last_event_index = i

        # fallback (stable anchor)
        if last_event_index is None:
            last_event_index = max(0, len(data) - STRUCTURE_WINDOW * 2)

        # ----------------------------
        # STEP 2: structure zone
        # ----------------------------
        monitor = data.iloc[last_event_index:]

        if len(monitor) < 5:
            return "NONE"

        structure_high = monitor['High'].max()
        structure_low  = monitor['Low'].min()
        mid = (structure_high + structure_low) / 2

        # ----------------------------
        # STEP 3: FIRST SHIFT (STRICT)
        # ----------------------------

        # 🟢 Fresh breakout UP (strict cross)
        if prev_close < structure_high and last_close >= structure_high:
            return "BUY"

        # 🔴 Fresh breakout DOWN (strict cross)
        if prev_close > structure_low and last_close <= structure_low:
            return "SELL"

        # ----------------------------
        # STEP 4: CONTINUOUS TREND
        # ----------------------------

        # Strong zones
        if last_close > structure_high:
            return "UP"

        if last_close < structure_low:
            return "DOWN"

        # Range bias (stable)
        return "UP" if last_close >= mid else "DOWN"

    except Exception:
        return "NONE"


def get_bos_bar(df):
    """
    Visual BOS Bar (FINAL)
    """

    try:
        signal = get_bos(df)

        if signal == "NONE":
            bar = Fore.LIGHTBLACK_EX + "░" * MAX_BAR_LENGTH
            return bar + Style.RESET_ALL, signal

        left_len = MAX_BAR_LENGTH // 2
        right_len = MAX_BAR_LENGTH - left_len

        # 🔥 Shift events (full color)
        if signal == "BUY":
            bar = Fore.GREEN + "█" * MAX_BAR_LENGTH

        elif signal == "SELL":
            bar = Fore.RED + "█" * MAX_BAR_LENGTH

        # 🧠 Trend state
        elif signal == "UP":
            bar = Fore.LIGHTBLACK_EX + "█" * left_len
            bar += Fore.GREEN + "█" * right_len

        else:  # DOWN
            bar = Fore.RED + "█" * left_len
            bar += Fore.LIGHTBLACK_EX + "█" * right_len

        return bar + Style.RESET_ALL, signal

    except Exception as e:
        return f"ERR: {e}", "ERR"
