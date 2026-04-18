from sysdthapxy import get_ha_data

# ANSI colors
GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"


def get_candle_visual(df=None, last_n=42):

    ha_close, ha_open, ha_color, df = get_ha_data(df=df)

    if ha_color is None:
        return ""

    # ==================================================
    # ARROW-BASED VISUAL (REPLACED CANDLES)
    # ==================================================
    visual = "".join([
        f"{GREEN}→{RESET}" if c == "green" else f"{RED}←{RESET}"
        for c in ha_color.iloc[-last_n:]
    ])

    return visual


# -------- Self-test --------
if __name__ == "__main__":
    visual = get_candle_visual()
    print(visual)
