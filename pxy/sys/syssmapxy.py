import pandas as pd
import numpy as np
import warnings
import os
from colorama import Fore, Style, init
from syscnfgpxy import SYSSMAPXY_MA_PERIOD, SYSSMAPXY_VARIANT

warnings.simplefilter(action='ignore', category=FutureWarning)
init(autoreset=True)

from sysdtafpxy import fetch_yf_data

def calculate_moving_average(
    close: pd.Series,
    period: int = SYSSMAPXY_MA_PERIOD,
    variant: str = SYSSMAPXY_VARIANT,
) -> pd.Series:
    """Calculate a simple moving average or linear-regression endpoint TSMA."""
    variant = str(variant).upper()
    if variant not in {"SMA", "TSMA"}:
        raise ValueError("variant must be SMA or TSMA.")
    if period < 1:
        raise ValueError("period must be a positive integer.")
    if variant == "SMA" or period == 1:
        return close.rolling(window=period).mean()

    x = np.arange(period, dtype=float)
    x_deviations = x - x.mean()
    variance_x = np.dot(x_deviations, x_deviations)

    def regression_endpoint(values):
        mean = values.mean()
        slope = np.dot(values - mean, x_deviations) / variance_x
        return mean + slope * x_deviations[-1]

    return close.rolling(window=period).apply(regression_endpoint, raw=True)


def get_sma(
    df: pd.DataFrame,
    period: int = SYSSMAPXY_MA_PERIOD,
    variant: str = SYSSMAPXY_VARIANT,
) -> dict:
    """Return the selected moving-average value and price-side status."""
    variant = str(variant).upper()
    if variant not in {"SMA", "TSMA"}:
        raise ValueError("variant must be SMA or TSMA.")
    if df is None or df.empty or len(df) < period:
        return {"value": 0.0, "status": "NA", "period": period, "variant": variant}
    from sysdthapxy import transform_dtha_ohlc
    df = transform_dtha_ohlc(df)
    column = "SMA" if variant == "SMA" else "TSMA"
    df[column] = calculate_moving_average(df["Close"], period=period, variant=variant)
    close_arr = df['Close'].to_numpy()
    sma_arr = df[column].to_numpy()
    # Extract latest valid calculations
    latest_close = close_arr[-1]
    latest_sma = sma_arr[-1]
    if np.isnan(latest_sma):
        return {"value": 0.0, "status": "NA", "period": period, "variant": variant}
    # Strict binary mapping based on current location relative to SMA 50
    status = "BULL" if latest_close >= latest_sma else "BEAR"
    return {
        "value": float(latest_sma),
        "status": status,
        "period": period,
        "variant": variant,
        "df_with_sma": df # Return df to pass to json exporter
    }


def get_sma_signal(
    df: pd.DataFrame,
    period: int = SYSSMAPXY_MA_PERIOD,
) -> dict:
    """Return the independent 50-period SMA value and price-side status."""
    return get_sma(df, period=period, variant="SMA")

def dump_ohlc_json(df: pd.DataFrame, target_folder_name: str = "web") -> None:
    """
    Constructs a trend-tracking candle over the configured moving-average window.
    O = Actual Open price at the start of the window (SMA delinked)
    H = Highest price point across the configured window
    L = Lowest price point across the configured window
    C = Current Live / Close price
    """
    if df is None or df.empty or len(df) < SYSSMAPXY_MA_PERIOD:
        print("Invalid data. Cannot dump single candle JSON.")
        return
    from sysdthapxy import transform_dtha_ohlc, publish_dtha_json_payload
    df = transform_dtha_ohlc(df)
    # 1. Grab the configured moving-average window for the range boundaries.
    window = df.iloc[-SYSSMAPXY_MA_PERIOD:]
    # 2. Extract values (opening price remains delinked from the average).
    open_price = window['Open'].iloc[0]
    highest_price = window['High'].max()
    lowest_price = window['Low'].min()
    current_close = window['Close'].iloc[-1]
    # Construct the tracking candle dictionary
    candle_data = [{
        'O': float(open_price),     # Actual open at the start of the window
        'H': float(highest_price),  # Highest price point in 50 candles
        'L': float(lowest_price),   # Lowest price point in 50 candles
        'C': float(current_close)   # Live price is close
    }]
    # Build absolute paths for sibling folder 'web'
    base_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(base_dir)
    sibling_dir = os.path.join(parent_dir, target_folder_name)
    # Ensure sibling folder exists
    os.makedirs(sibling_dir, exist_ok=True)
    # Save (always replaces existing file)
    json_path = os.path.join(sibling_dir, 'websmapxy.json')
    # Dump directly using pandas frame
    publish_dtha_json_payload(candle_data, json_path, indent=4)
    print(f"Custom Trend Candle replaced successfully at: {json_path}")

if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        result = get_sma(df)
        if result["status"] == "BULL":
            color = Fore.GREEN + Style.BRIGHT
            output = "🟢 PRICE MOVING BULL 🟢".center(40)
        elif result["status"] == "BEAR":
            color = Fore.RED + Style.BRIGHT
            output = "🔴 PRICE MOVING BEAR 🔴".center(40)
        else:
            color = Fore.WHITE
            output = "PRICE DIRECTION UNKNOWN".center(40)
        print(f"\n{color}{output}{Style.RESET_ALL}\n")
        # Dump the custom window row to the 'web' folder
        if "df_with_sma" in result:
            dump_ohlc_json(result["df_with_sma"], target_folder_name="web")
