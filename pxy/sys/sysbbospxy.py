# exebbospxy.py

from colorama import Fore, Style, init
init(autoreset=True)

STRUCTURE_MINUTES = 60    # last 60 mins for structure
MAX_BAR_LENGTH = 42       # bar width

def get_bos(df):
    """
    Returns 'BULL' or 'BEAR' based on the last 60 min structure
    df -> must be 1-min OHLC dataframe
    """
    try:
        if df is None or len(df) < STRUCTURE_MINUTES + 2:
            return "NO DATA"

        # Last 60 mins excluding running candle
        recent = df.iloc[-STRUCTURE_MINUTES-1:-1]

        structure_high = recent['High'].max()
        structure_low  = recent['Low'].min()

        mid = (structure_high + structure_low) / 2
        last_close = df.iloc[-2]['Close']

        return "BULL" if last_close >= mid else "BEAR"

    except Exception:
        return "ERR"


def get_bos_bar(df):
    """
    Returns a visual bar for BOS like candle:
    - GREEN if BULL
    - RED if BEAR
    - Starts from middle reference
    """
    try:
        bos = get_bos(df)
        if bos in ["NO DATA", "ERR"]:
            return bos, bos  # return both

        recent = df.iloc[-STRUCTURE_MINUTES-1:-1]
        structure_high = recent['High'].max()
        structure_low  = recent['Low'].min()
        mid = (structure_high + structure_low) / 2
        last_close = df.iloc[-2]['Close']

        if bos == "BULL":
            # BULL → fill right from middle
            left_len = MAX_BAR_LENGTH // 2
            right_len = MAX_BAR_LENGTH - left_len
            bar = Fore.LIGHTBLACK_EX + '█' * left_len
            bar += Fore.GREEN + '█' * right_len
        else:
            # BEAR → fill left from middle
            right_len = MAX_BAR_LENGTH // 2
            left_len = MAX_BAR_LENGTH - right_len
            bar = Fore.RED + '█' * left_len
            bar += Fore.LIGHTBLACK_EX + '█' * right_len

        return bar + Style.RESET_ALL, bos

    except Exception as e:
        return f"ERR: {e}", "ERR"
