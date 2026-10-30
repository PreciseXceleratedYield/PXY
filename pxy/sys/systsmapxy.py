
import numpy as np
import pandas as pd

from syscnfgpxy import SYSSMAPXY_TSMA_PERIOD
from syssmapxy import calculate_moving_average
from sysdtafpxy import fetch_yf_data


def getsystsmapxy(
    df: pd.DataFrame = None,
    length: int = SYSSMAPXY_TSMA_PERIOD,
) -> pd.DataFrame:
    """
    Calculate clean linear-regression endpoint TSMA from DTAF Close.

    No averaging with raw Close.
    Trend compares current TSMA with previous TSMA.
    """

    if df is None or df.empty or "Close" not in df.columns:
        df = fetch_yf_data()
        if df is None or df.empty:
            return pd.DataFrame()

    df = df.copy()

    if isinstance(length, bool) or not isinstance(length, int) or length < 2:
        raise ValueError("TSMA length must be an integer of at least 2.")

    if len(df) < length:
        return df

    df["final_close"] = calculate_moving_average(
        df["Close"],
        period=length,
        variant="TSMA",
    )

    df["sma_trend_full"] = np.where(
        df["final_close"] > df["final_close"].shift(1),
        "BULL",
        np.where(
            df["final_close"] < df["final_close"].shift(1),
            "BEAR",
            "NONE",
        ),
    )

    df.loc[
        df["final_close"].isna() | df["final_close"].shift(1).isna(),
        "sma_trend_full",
    ] = "NONE"

    latest_val = float(df["final_close"].iloc[-1])
    latest_state = str(df["sma_trend_full"].iloc[-1])

    color_code = (
        "\033[92m" if latest_state == "BULL"
        else "\033[91m" if latest_state == "BEAR"
        else "\033[93m"
    )

    print(
        f"{color_code}"
        f"{f' {latest_state} <{latest_val:.2f}> ' :~^42}"
        f"\033[0m"
    )

    return df


if __name__ == "__main__":
    getsystsmapxy()
