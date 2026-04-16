from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_WINDOW = 14
MAX_BAR_LENGTH = 42


def get_bos(df):
    """
    Continuous Structure Trend
    Returns: UP / DOWN / NONE
    """

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 5:
            return "NONE"

        data = df.iloc[:-1].copy()
        last_close = data['Close'].iloc[-1]

        # ----------------------------
        # STEP 1: detect last swing event
        # ----------------------------
        last_event_index = None

        for i in range(STRUCTURE_WINDOW, len(data)):
            window = data.iloc[i-STRUCTURE_WINDOW:i]

            high = window['High'].max()
            low  = window['Low'].min()
            close = data['Close'].iloc[i]

            if close >= high or close <= low:
                last_event_index = i

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
        # STEP 3: STRUCTURE TREND
        # ----------------------------

        # Strong breakout zones
        if last_close >= structure_high:
            return "UP"

        elif last_close <= structure_low:
            return "DOWN"

        # Inside range → bias from mid
        if last_close >= mid:
            return "UP"
        else:
            return "DOWN"

    except Exception:
        return "NONE"


def get_bos_bar(df):
    """
    Visual Structure Trend Bar (UP / DOWN)
    """

    try:
        signal = get_bos(df)

        # Empty
        if signal == "NONE":
            bar = Fore.LIGHTBLACK_EX + "░" * MAX_BAR_LENGTH
            return bar + Style.RESET_ALL, signal

        # Bar rendering
        left_len = MAX_BAR_LENGTH // 2
        right_len = MAX_BAR_LENGTH - left_len

        if signal == "UP":
            bar = Fore.LIGHTBLACK_EX + "█" * left_len
            bar += Fore.GREEN + "█" * right_len

        else:  # DOWN
            bar = Fore.RED + "█" * left_len
            bar += Fore.LIGHTBLACK_EX + "█" * right_len

        return bar + Style.RESET_ALL, signal

    except Exception as e:
        return f"ERR: {e}", "ERR"
