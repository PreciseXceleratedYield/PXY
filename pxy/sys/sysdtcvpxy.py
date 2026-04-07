# sysdthapxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data

# 🔥 CONTROL: Keep forming candle INCLUDED
USE_FORMING_CANDLE = True


def get_ha_data(tickerSymbol=None, df=None):
    """
    Compute raw Close comparisons and colors (replaces HA logic)
    while keeping original naming conventions and signature.

    Returns:
        c1_close (pd.Series) -> raw Close
        c2_close (pd.Series) -> dummy Open (for compatibility)
        c3_close (pd.Series) -> same as c1_close (placeholder for future comparisons)
        c_color  (pd.Series) -> "green" / "red" / "none"
        df       (pd.DataFrame)
    """

    # ---------------- FETCH DATA ----------------
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return None, None, None, None, df

    # ---------------- FORMING CANDLE CONTROL ----------------
    if USE_FORMING_CANDLE is False:
        df = df.iloc[:-1]

    # ---------------- VALIDATE REQUIRED COLUMNS ----------------
    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, None, df

    # ---------------- RAW CLOSE ----------------
    c1_close = df['Close']
    c3_close = df['Close']  # placeholder series for future logic

    # ---------------- DUMMY OPEN (for compatibility) ----------------
    c2_close = pd.Series(index=c1_close.index, dtype='float64')
    if len(c1_close) > 0:
        c2_close.iloc[0] = df['Open'].iloc[0]
        for i in range(1, len(c1_close)):
            c2_close.iloc[i] = c2_close.iloc[i - 1]  # dummy, unused

    # ---------------- COLOR LOGIC ----------------
    c_color = pd.Series(index=c1_close.index, dtype='object')

    for i in range(len(c1_close)):
        if i == 0 or pd.isna(c1_close.iloc[i]) or pd.isna(c1_close.iloc[i-1]):
            c_color.iloc[i] = "none"
        else:
            curr_close = c1_close.iloc[i]
            prev_close = c1_close.iloc[i - 1]

            if curr_close > prev_close:
                c_color.iloc[i] = "green"
            elif curr_close < prev_close:
                c_color.iloc[i] = "red"
            elif curr_close == prev_close:
                prev_color = c_color.iloc[i - 1]
                if prev_color == "green":
                    c_color.iloc[i] = "green"
                elif prev_color == "red":
                    c_color.iloc[i] = "red"
                else:
                    c_color.iloc[i] = "none"
            else:
                c_color.iloc[i] = "none"

    return c1_close, c2_close, c3_close, c_color, df


# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    c1_close, c2_close, c3_close, c_color, df = get_ha_data()

    print("\n" + "="*60)
    print("RAW CLOSE STRICT DEBUG (FINAL PRO VERSION)")
    print("="*60)

    if c1_close is None:
        print("Close calculation failed")
    else:
        print("\nLast 5 c1_close Values:")
        print(c1_close.tail())

        print("\nLast 5 c2_close (Dummy Opens):")
        print(c2_close.tail())

        print("\nLast 5 c3_close Values:")
        print(c3_close.tail())

        print("\nLast 5 c_color Values:")
        print(c_color.tail())

        print("\nLast Candle Breakdown:")
        print(f"c1_close : {c1_close.iloc[-1]}")
        print(f"c2_close : {c2_close.iloc[-1]} (dummy)")
        print(f"c3_close : {c3_close.iloc[-1]}")
        print(f"c_color  : {c_color.iloc[-1]}")
