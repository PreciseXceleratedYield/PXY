"""DTAF-owned raw OC direction, independent of DTHA and TSMAC1."""

import pandas as pd


def get_raw_oc_direction(df=None):
    """C1 = previous completed raw close; C0 = current running raw close."""
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
    if df is None or len(df) < 2 or "Close" not in df.columns:
        return None, "NONE"
    closes = pd.to_numeric(df["Close"].iloc[-2:], errors="coerce")
    if closes.isna().any():
        return None, "NONE"
    c1, c0 = map(float, closes)
    if not all(map(__import__("math").isfinite, (c1, c0))) or c1 <= 0 or c0 <= 0:
        return None, "NONE"
    return c0, ("UP" if c0 > c1 else "DOWN" if c0 < c1 else "NONE")


def get_raw_oc_signals(df=None):
    price, direction = get_raw_oc_direction(df)
    return price, {"UP": "BUY", "DOWN": "SELL"}.get(direction, "NONE"), {"UP": "BULL", "DOWN": "BEAR"}.get(direction, "SIDE")
