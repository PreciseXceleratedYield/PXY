# sysdeptpxy.py

# -------------------- CONFIG SWITCH --------------------
candle = "cv"  # set to "ha" or "cv"
candle = candle.lower()

if candle == "ha":
    from sysdthapxy import get_ha_data
elif candle == "cv":
    from sysdtcvpxy import get_ha_data
else:
    raise ValueError(f"Invalid candle type: {candle}. Must be 'ha' or 'cv'.")

# -------------------- IMPORTS --------------------
import pandas as pd

# -------------------- CANDLE VISUAL --------------------
def get_candle_visual(df=None, last_n=21):
    """
    Returns a simple string visual of last_n candles using emoji:
    🟢 for green, 🔴 for red
    Works for both HA and CV candles.
    """

    # ---------------- FETCH DATA ----------------
    c1_close, c2_close, c_color, df = get_ha_data(df=df)

    if c_color is None or df is None or df.empty:
        return ""

    visual = "".join(["🟢" if c == "green" else "🔴" for c in c_color.iloc[-last_n:]])
    return visual

# -------------------- SELF TEST --------------------
if __name__ == "__main__":
    visual = get_candle_visual()
    print(visual)
