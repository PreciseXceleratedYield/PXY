# sysdthapxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data

# 🔥 CONTROL: Keep forming candle INCLUDED
USE_FORMING_CANDLE = True


def get_ha_data(tickerSymbol=None, df=None):
    """
    Pure c1 vs c2 comparison to define color.
    
    Returns:
        c1_close (pd.Series) -> raw Close
        c2_close (pd.Series) -> previous raw Close (for reference)
        c_color  (pd.Series) -> "green" / "red" / "none"
        df       (pd.DataFrame)
    """

    # ---------------- FETCH DATA ----------------
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return None, None, None, df

    # ---------------- FORMING CANDLE CONTROL ----------------
    if USE_FORMING_CANDLE is False:
        df = df.iloc[:-1]

    # ---------------- VALIDATE REQUIRED COLUMNS ----------------
    if 'Close' not in df.columns:
        return None, None, None, df

    # ---------------- RAW CLOSE ----------------
    c1_close = df['Close']

    # ---------------- PREVIOUS CLOSE SERIES ----------------
    c2_close = c1_close.shift(1)  # previous candle close

    # ---------------- COLOR LOGIC ----------------
    c_color = pd.Series(index=c1_close.index, dtype='object')
    for i in range(len(c1_close)):
        curr = c1_close.iloc[i]
        prev = c2_close.iloc[i]

        if pd.isna(curr) or pd.isna(prev):
            c_color.iloc[i] = "none"
        elif curr > prev:
            c_color.iloc[i] = "green"
        elif curr < prev:
            c_color.iloc[i] = "red"
        else:  # curr == prev
            if i == 0:
                c_color.iloc[i] = "none"
            else:
                c_color.iloc[i] = c_color.iloc[i-1]  # repeat previous color

    return c1_close, c2_close, c_color, df


# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    c1_close, c2_close, c_color, df = get_ha_data()

    print("\n" + "="*60)
    print("PURE C1 vs C2 CLOSE DEBUG")
    print("="*60)

    print("\nLast 5 c1_close Values:")
    print(c1_close.tail())

    print("\nLast 5 c2_close Values:")
    print(c2_close.tail())

    print("\nLast 5 c_color Values:")
    print(c_color.tail())

    print("\nLast Candle Breakdown:")
    print(f"c1_close : {c1_close.iloc[-1]}")
    print(f"c2_close : {c2_close.iloc[-1]}")
    print(f"c_color  : {c_color.iloc[-1]}")
