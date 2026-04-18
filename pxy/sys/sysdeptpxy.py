from sysdthapxy import get_ha_data

# ANSI colors
GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"


def get_candle_visual(df=None, last_n=42):

    ha_close, ha_open, ha_color, df = get_ha_data(df=df)

    # safety check
    if ha_close is None or ha_open is None:
        return ""

    # ==================================================
    # FIXED CORE LOGIC (NO STRING COLOR RELIANCE)
    # Bull = HA Close > HA Open
    # Bear = HA Close < HA Open
    # ==================================================
    direction = ha_close > ha_open

    # ==================================================
    # VISUAL STREAM
    # + = bullish candle
    # - = bearish candle
    # ==================================================
    visual = "".join([
        f"{GREEN}/{RESET}" if is_bull else f"{RED}\{RESET}"
        for is_bull in direction.iloc[-last_n:]
    ])

    return visual


# -------- Self-test --------
if __name__ == "__main__":
    print(get_candle_visual())
