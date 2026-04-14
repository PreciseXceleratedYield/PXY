from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_WINDOW = 14
MAX_BAR_LENGTH = 42


def get_bos(df):
    """
    Event-anchored swing system (FIXED VERSION):
    - no global state
    - correct swing detection
    - stable structure anchoring
    """

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 5:
            return "NONE"

        data = df.iloc[:-1].copy()   # exclude running candle safely
        last_close = data['Close'].iloc[-1]

        # ----------------------------
        # STEP 1: detect last real swing event
        # ----------------------------
        last_event_index = None

        for i in range(STRUCTURE_WINDOW, len(data)):
            window = data.iloc[i-STRUCTURE_WINDOW:i]

            high = window['High'].max()
            low  = window['Low'].min()
            close = data['Close'].iloc[i]

            # FIXED: only mark structural extremes (not every candle)
            if close >= high or close <= low:
                last_event_index = i

        # fallback anchor (important fix)
        if last_event_index is None:
            last_event_index = max(0, len(data) - STRUCTURE_WINDOW * 2)

        # ----------------------------
        # STEP 2: structure after event
        # ----------------------------
        monitor = data.iloc[last_event_index:]

        if len(monitor) < 5:
            return "NONE"

        structure_high = monitor['High'].max()
        structure_low  = monitor['Low'].min()
        mid = (structure_high + structure_low) / 2

        # ----------------------------
        # STEP 3: breakout logic
        # ----------------------------
        if last_close > structure_high:
            return "BBUY"

        elif last_close < structure_low:
            return "BSELL"

        # ----------------------------
        # STEP 4: continuation zones
        # ----------------------------
        if mid < last_close < structure_high:
            return "RBUY"

        elif structure_low < last_close < mid:
            return "RSELL"

        return "NONE"

    except Exception:
        return "NONE"


def get_bos_bar(df, c1_col=None, c2_col=None):
    """
    Visual BOS bar (same structure, safer logic)
    """

    try:
        signal = get_bos(df)

        if signal not in ["NONE", "ERR"] and c1_col and c2_col:
            try:
                last_c1 = df.iloc[-1][c1_col]
                last_c2 = df.iloc[-2][c2_col]

                if signal in ["BBUY", "RBUY"]:
                    if last_c1 < last_c2:
                        signal = "NONE"

                elif signal in ["BSELL", "RSELL"]:
                    if last_c1 > last_c2:
                        signal = "NONE"

            except Exception:
                signal = "ERR"

        # ✅ ONLY CHANGE: return empty bar instead of "NONE"
        if signal in ["NONE", "ERR"]:
            bar = Fore.LIGHTBLACK_EX + "░" * MAX_BAR_LENGTH
            return bar + Style.RESET_ALL, signal

        # ----- ORIGINAL BAR LOGIC (UNCHANGED) -----
        left_len = MAX_BAR_LENGTH // 2
        right_len = MAX_BAR_LENGTH - left_len

        if signal in ["BBUY", "RBUY"]:
            bar = Fore.LIGHTBLACK_EX + "█" * left_len
            bar += Fore.GREEN + "█" * right_len
        else:
            bar = Fore.RED + "█" * left_len
            bar += Fore.LIGHTBLACK_EX + "█" * right_len

        return bar + Style.RESET_ALL, signal

    except Exception as e:
        return f"ERR: {e}", "ERR"
