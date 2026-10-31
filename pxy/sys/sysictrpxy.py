import json
import os
import warnings
import numpy as np
import pandas as pd
import syscnfgpxy
from syssmapxy import calculate_moving_average
from systsmpxy import calculate_tsma
from sysstrnpxy import calculate_supertrend as calculate_st

TIMEZONE = syscnfgpxy.SYSCNFGPXY_TIMEZONE
TSMA_PERIOD = syscnfgpxy.SYSSMAPXY_TSMA_PERIOD
SMA_PERIOD = syscnfgpxy.SYSSMAPXY_MA_PERIOD
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
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    tz_string = str(TIMEZONE)
    df = df.tz_convert(tz_string) if df.index.tz is not None else df.tz_localize("UTC").tz_convert(tz_string)
    df = calculate_st(df)
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
    latest = df.iloc[-1]
    return {
        "tsma": str(latest.get("TSMA_Trend", "NA")),
        "sma": str(latest.get("SMA_Trend", "NA")),
        "st": str(latest.get("ST_Trend", "SIDE")),
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
    output = []
    for idx, row in df.iterrows():
        st_val = float(row["st_line"]) if not pd.isna(row["st_line"]) else 0.0
        mirror_val = float(row["st_mirror"]) if not pd.isna(row["st_mirror"]) else 0.0
        sma_val = float(row["sma_50"]) if not pd.isna(row.get("sma_50")) else None
        tsma_val = float(row["tsma_50"]) if not pd.isna(row.get("tsma_50")) else None
        output.append({
            "time": int(idx.timestamp()),
            "open": float(row["Open"]) if not pd.isna(row["Open"]) else 0.0,
            "high": float(row["High"]) if not pd.isna(row["High"]) else 0.0,
            "low": float(row["Low"]) if not pd.isna(row["Low"]) else 0.0,
            "close": float(row["Close"]),
            "st_line": st_val,
            "mirror_line": mirror_val,
            "sma50": sma_val,
            "tsma50": tsma_val,
            "trend": str(row.get("ST_Trend", "SIDE")),
            "sma_trend": str(row.get("SMA_Trend", "NA")),
            "tsma_trend": str(row.get("TSMA_Trend", "NA")),
        })
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
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
