# exebbospxy.py

from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_MINUTES = 60    # last 60 mins for structure
MAX_BAR_LENGTH = 42       # bar width

def get_bos(df):
    """
    Returns breakout or reversal signal based on the last 60 min structure:
    - BBUY, BSELL, RBUY, RSELL, or 'NONE'
    df -> must be 1-min OHLC dataframe
    """
    try:
        if df is None or len(df) < STRUCTURE_MINUTES + 2:
            return "NONE"

        # Last 60 mins excluding running candle
        recent = df.iloc[-STRUCTURE_MINUTES-1:-1]

        structure_high = recent['High'].max()
        structure_low  = recent['Low'].min()
        mid = (structure_high + structure_low) / 2
        last_close = df.iloc[-2]['Close']

        # Breakout detection
        if last_close > structure_high:
            return "BBUY"
        elif last_close < structure_low:
            return "BSELL"

        # Reversal detection
        if mid < last_close < structure_high:
            return "RBUY"
        elif structure_low < last_close < mid:
            return "RSELL"

        return "NONE"

    except Exception:
        return "ERR"


def get_bos_bar(df, c1_col=None, c2_col=None):
    """
    Returns a visual bar for BOS-like signal:
    - GREEN for BBUY / RBUY
    - RED for BSELL / RSELL
    - Starts from middle reference
    - If C1/C2 comparison fails, signal is treated as NONE
    """
    try:
        signal = get_bos(df)

        # Apply C1/C2 check internally
        if signal not in ["NONE", "ERR"] and c1_col and c2_col:
            try:
                last_c1 = df.iloc[-2][c1_col]
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

        # Last 60 mins excluding running candle
        recent = df.iloc[-STRUCTURE_MINUTES-1:-1]
        structure_high = recent['High'].max()
        structure_low  = recent['Low'].min()

        left_len = MAX_BAR_LENGTH // 2
        right_len = MAX_BAR_LENGTH - left_len

        if signal in ["BBUY", "RBUY"]:
            bar = Fore.LIGHTBLACK_EX + '█' * left_len
            bar += Fore.GREEN + '█' * right_len
        else:  # BSELL or RSELL
            bar = Fore.RED + '█' * left_len
            bar += Fore.LIGHTBLACK_EX + '█' * right_len

        return bar + Style.RESET_ALL, signal

    except Exception as e:
        return f"ERR: {e}", "ERR"
