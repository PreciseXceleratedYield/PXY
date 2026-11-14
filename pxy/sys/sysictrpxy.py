import json
import os
import warnings
import numpy as np
import pandas as pd
import syscnfgpxy
from sysdthapxy import transform_dtha_ohlc, publish_dtha_json_payload
from syssmapxy import calculate_moving_average, get_sma_signal
from systsmpxy import calculate_tsma, get_tsma
from sysstrnpxy import calculate_supertrend as calculate_st, get_market_trend
from sysstftypxy import calculate_st50

TIMEZONE = syscnfgpxy.SYSCNFGPXY_TIMEZONE
TSMA_PERIOD = syscnfgpxy.SYSSMAPXY_TSMA_PERIOD
SMA_PERIOD = syscnfgpxy.SYSSMAPXY_MA_PERIOD
SMA50_VARIANT = syscnfgpxy.SMA50_VARIANT
warnings.simplefilter(action="ignore", category=FutureWarning)

DEFAULT_CHART_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "webchrtpxy.json",
)


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate ST, ST Mirror, SMA-50, and TSMA-7 on one supplied snapshot."""
    if df is None:
        return pd.DataFrame()
    if df.empty:
        from sysdtafpxy import fetch_yf_data
        try:
            raw_df = fetch_yf_data(period="3d", interval="1m")
            if raw_df is not None and not raw_df.empty:
                df = raw_df.copy()
        except Exception:
            return df.copy()
    if df.empty:
        return df
    # DTHA is the only candle transformation authority.
    df = transform_dtha_ohlc(df)
    required_ohlc = ("Open", "High", "Low", "Close")
    for column in required_ohlc:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    valid = np.isfinite(df[list(required_ohlc)]).all(axis=1)
    valid &= (df[list(required_ohlc)] > 0).all(axis=1)
    valid &= df["High"] >= df[["Open", "Low", "Close"]].max(axis=1)
    valid &= df["Low"] <= df[["Open", "High", "Close"]].min(axis=1)
    df = df.loc[valid].copy()
    if df.empty:
        return df
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    tz_string = str(TIMEZONE)
    df = df.tz_convert(tz_string) if df.index.tz is not None else df.tz_localize("UTC").tz_convert(tz_string)
    df = calculate_st(df)
    if SMA50_VARIANT == "ST50":
        df = calculate_st50(df)
        df["sma_50"] = df["st50"]
    else:
        df["sma_50"] = calculate_moving_average(df["Close"], period=SMA_PERIOD, variant="SMA")
    df["tsma_50"] = calculate_tsma(df["Close"], period=TSMA_PERIOD)
    close = pd.to_numeric(df["Close"], errors="coerce")
    sma = pd.to_numeric(df["sma_50"], errors="coerce")
    tsma = pd.to_numeric(df["tsma_50"], errors="coerce")
    df["SMA_Trend"] = np.select([sma.isna(), close >= sma], ["NA", "BULL"], default="BEAR")
    df["TSMA_Trend"] = np.select([tsma.isna(), close >= tsma], ["NA", "BULL"], default="BEAR")
    return df


def get_indicator_signals(df: pd.DataFrame) -> dict:
    """Return the latest independent TSMA, SMA, and ST classifications."""
    if df is None or df.empty:
        return {"tsma": "NA", "sma": "NA", "st": "SIDE"}
    required = {"TSMA_Trend", "SMA_Trend", "ST_Trend"}
    if not required.issubset(df.columns):
        df = calculate_indicators(df)
    if df is None or df.empty:
        return {"tsma": "NA", "sma": "NA", "st": "SIDE"}
    tsma_result = get_tsma(df, period=TSMA_PERIOD)
    sma_result = {"status": str(df["SMA_Trend"].iloc[-1])}
    return {
        "tsma": tsma_result.get("status", "NA"),
        "sma": sma_result.get("status", "NA"),
        "st": get_market_trend(df),
    }


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Compatibility interface returning the complete indicator frame."""
    return calculate_indicators(df)


def export_supertrend_json(df: pd.DataFrame = None, output_file=DEFAULT_CHART_OUTPUT):
    """Export combined indicator history using the existing chart JSON fields."""
    if df is None or df.empty:
        df = calculate_indicators(pd.DataFrame())
    elif not {"sma_50", "tsma_50", "ST_Trend"}.issubset(df.columns):
        df = calculate_indicators(df)
    if df is None or df.empty:
        return None
    def finite_number(value):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if np.isfinite(number) else None

    output = []
    for idx, row in df.iterrows():
        open_val = finite_number(row.get("Open"))
        high_val = finite_number(row.get("High"))
        low_val = finite_number(row.get("Low"))
        close_val = finite_number(row.get("Close"))
        if any(value is None or value <= 0 for value in (open_val, high_val, low_val, close_val)):
            continue
        st_val = finite_number(row.get("st_line"))
        mirror_val = finite_number(row.get("st_mirror"))
        output.append({
            "time": int(idx.timestamp()),
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "st_line": st_val if st_val is not None and st_val > 0 else None,
            "mirror_line": mirror_val if mirror_val is not None and mirror_val > 0 else None,
            "sma50": finite_number(row.get("sma_50")),
            "sma_variant": SMA50_VARIANT,
            "tsma50": finite_number(row.get("tsma_50")),
            "trend": str(row.get("ST_Trend", "SIDE")),
            "sma_trend": str(row.get("SMA_Trend", "NA")),
            "tsma_trend": str(row.get("TSMA_Trend", "NA")),
        })
    if not output:
        return None
    publish_dtha_json_payload(output, output_file, indent=2)
    return output


if __name__ == "__main__":
    if os.environ.get("PXY_MONITOR_MODE") == "1":
        from sysdtafpxy import fetch_yf_data_for_monitor
        source_df = fetch_yf_data_for_monitor(period="3d", interval="1m")
    else:
        from sysdtafpxy import fetch_yf_data
        source_df = fetch_yf_data(period="3d", interval="1m")
    processed_df = calculate_indicators(source_df if source_df is not None else pd.DataFrame())
    if processed_df is not None and not processed_df.empty:
        target_index = processed_df.index[-1]
        signals = get_indicator_signals(processed_df)
        print(f"Timestamp : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Price     : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"ST        : {float(processed_df.at[target_index, 'st_line']):.2f} | Mirror: {float(processed_df.at[target_index, 'st_mirror']):.2f}")
        print(f"Indicators: TSMA={signals['tsma']} | SMA={signals['sma']} | ST={signals['st']}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
