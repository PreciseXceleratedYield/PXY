# exebbospxy.py

from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_WINDOW = 14
MAX_BAR_LENGTH = 42

# 🔥 stores last detected swing event index
_last_event_index = None


def get_bos(df):
    """
    Event-anchored swing system:
    1. Find last reversal (swing event)
    2. Use that as anchor
    3. Monitor structure AFTER that event only
    """
    global _last_event_index

    try:
        if df is None or len(df) < STRUCTURE_WINDOW + 5:
            return "NONE"

        data = df.iloc[:-1]  # exclude running candle
        last_close = df.iloc[-2]['Close']

        # ----------------------------
        # STEP 1: detect last swing (reversal event)
        # ----------------------------
        for i in range(STRUCTURE_WINDOW, len(data)):
            window = data.iloc[i-STRUCTURE_WINDOW:i]

            high = window['High'].max()
            low  = window['Low'].min()
            mid = (high + low) / 2

            close = data['Close'].iloc[i]

            # reversal detection (your original logic)
            if mid < close < high or low < close < mid:
                _last_event_index = i

        # fallback if nothing found
        if _last_event_index is None:
            _last_event_index = len(data) - STRUCTURE_WINDOW

        # ----------------------------
        # STEP 2: build swing structure AFTER event
        # ----------------------------
        start = _last_event_index
        monitor = data.iloc[start:]

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
        # STEP 4: continuation/reversal zones
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
    Visual bar (UNCHANGED LOGIC)
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

        if signal in ["NONE", "ERR"]:
            return signal, signal

        recent = df.iloc[-STRUCTURE_WINDOW-1:-1]

        left_len = MAX_BAR_LENGTH // 2
        right_len = MAX_BAR_LENGTH - left_len

        if signal in ["BBUY", "RBUY"]:
            bar = Fore.LIGHTBLACK_EX + '█' * left_len
            bar += Fore.GREEN + '█' * right_len
        else:
            bar = Fore.RED + '█' * left_len
            bar += Fore.LIGHTBLACK_EX + '█' * right_len

        return bar + Style.RESET_ALL, signal

    except Exception as e:
        return f"ERR: {e}", "ERR"
