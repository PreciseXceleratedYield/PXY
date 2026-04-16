from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_WINDOW = 14
MAX_BAR_LENGTH = 42


def get_bos(df):
    """
    Clean BOS (No pullbacks, no repeats)
    """

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 5:
            return "NONE"

        data = df.iloc[:-1].copy()
        last_close = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2]

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

        # ----------------------------
        # STEP 3: BREAKOUT ONLY
        # ----------------------------

        # 🟢 Fresh break UP
        if last_close > structure_high and prev_close <= structure_high:
            return "BBUY"

        # 🔴 Fresh break DOWN
        elif last_close < structure_low and prev_close >= structure_low:
            return "BSELL"

        return "NONE"

    except Exception:
        return "NONE"


def get_bos_bar(df, c1_col=None, c2_col=None):
    """
    Visual BOS bar (updated for BBUY / BSELL)
    """

    try:
        signal = get_bos(df)

        # Optional filter
        if signal not in ["NONE", "ERR"] and c1_col and c2_col:
            try:
                last_c1 = df.iloc[-1][c1_col]
                last_c2 = df.iloc[-2][c2_col]

                if signal == "BBUY" and last_c1 < last_c2:
                    signal = "NONE"

                elif signal == "BSELL" and last_c1 > last_c2:
                    signal = "NONE"

            except Exception:
                signal = "ERR"

        # Empty bar
        if signal in ["NONE", "ERR"]:
            bar = Fore.LIGHTBLACK_EX + "░" * MAX_BAR_LENGTH
            return bar + Style.RESET_ALL, signal

        # Bar rendering
        left_len = MAX_BAR_LENGTH // 2
        right_len = MAX_BAR_LENGTH - left_len

        if signal == "BBUY":
            bar = Fore.LIGHTBLACK_EX + "█" * left_len
            bar += Fore.GREEN + "█" * right_len
        else:  # BSELL
            bar = Fore.RED + "█" * left_len
            bar += Fore.LIGHTBLACK_EX + "█" * right_len

        return bar + Style.RESET_ALL, signal

    except Exception as e:
        return f"ERR: {e}", "ERR"
