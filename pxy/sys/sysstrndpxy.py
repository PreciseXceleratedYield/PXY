import json
import os
import warnings
import numpy as np
import pandas as pd
from syscnfgpxy import TIMEZONE
from sysdtafpxy import fetch_yf_data

warnings.simplefilter(action='ignore', category=FutureWarning)

DEBUG_MODE = False

# ==============================================================================
# 🎛️ MASTER CONFIGURATION LAYER
# ==============================================================================
CONFIG = {
    "ST1": {
        "PERIOD": 3.0,   # Fast Supertrend Period
        "FACTOR": 1.4    # Fast Supertrend Multiplier
    },
    "ST2": {
        "PERIOD": 3.0,   # Slow Supertrend Period
        "FACTOR": 1.4    # Slow Supertrend Multiplier
    }
}
# ==============================================================================


def _compute_single_st(df: pd.DataFrame, period: float, factor: float) -> tuple:
    """Helper to compute standard Supertrend bands and an absolute inverse mirror line."""
    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    close = df['Close'].to_numpy()

    tr1 = high - low
    close_shifted = df['Close'].shift(1).to_numpy()
    if len(close_shifted) > 0:
        close_shifted[0] = close[0]

    tr2 = np.abs(high - close_shifted)
    tr3 = np.abs(low - close_shifted)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    atr = pd.Series(tr, index=df.index).ewm(alpha=1 / period, adjust=False).mean().to_numpy()

    hl2 = (high + low) / 2
    basic_upper = hl2 + (factor * atr)
    basic_lower = hl2 - (factor * atr)

    length = len(df)
    final_upper = np.zeros(length)
    final_lower = np.zeros(length)
    supertrend = np.zeros(length)
    mirror_line = np.zeros(length)
    st_trend = []

    # Persistent Anchor Point tracking variable
    anchor_price = hl2[0] if length > 0 else 0.0

    for i in range(length):
        if i == 0:
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
            supertrend[i] = final_upper[i]
            st_trend.append('BEAR')
            mirror_line[i] = anchor_price - (supertrend[i] - anchor_price)
            continue

        prev_upper = final_upper[i - 1]
        prev_lower = final_lower[i - 1]
        prev_trend = st_trend[i - 1]

        # Final Upper Band locking logic
        if basic_upper[i] < prev_upper or close[i - 1] > prev_upper:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = prev_upper

        # Final Lower Band locking logic
        if basic_lower[i] > prev_lower or close[i - 1] < prev_lower:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = prev_lower

        # Secure Direction State Switches & Anchor Capture on Trend Jump
        if prev_trend == 'BEAR':
            if close[i] > final_upper[i]:
                st_trend.append('BULL')
                supertrend[i] = final_lower[i]
                anchor_price = hl2[i]  # Capture Anchor on Jump
            else:
                st_trend.append('BEAR')
                supertrend[i] = final_upper[i]
        else:  # prev_trend == 'BULL'
            if close[i] < final_lower[i]:
                st_trend.append('BEAR')
                supertrend[i] = final_upper[i]
                anchor_price = hl2[i]  # Capture Anchor on Jump
            else:
                st_trend.append('BULL')
                supertrend[i] = final_lower[i]

        # Compute the absolute inverse slope line mirror
        st_distance_from_anchor = supertrend[i] - anchor_price
        mirror_line[i] = anchor_price - st_distance_from_anchor

    return pd.Series(supertrend, index=df.index), pd.Series(mirror_line, index=df.index)


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates Dual Supertrends and applies the 3-Zone Market Classifier logic.
    
    BULL: Price > Max(ST, Mirror)
    BEAR: Price < Min(ST, Mirror)
    SIDE: Price is inside/between the two boundaries
    """
    try:
        raw_df = fetch_yf_data(period='3d', interval='1m')
        if raw_df is not None and not raw_df.empty:
            df = raw_df.copy()
    except Exception as e:
        if DEBUG_MODE:
            print(f'Warning: Shared pipeline download fallback active | {e}')
        df = df.copy()

    if df.empty:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    tz_string = str(TIMEZONE)
    df = (
        df.tz_convert(tz_string)
        if df.index.tz is not None
        else df.tz_localize('UTC').tz_convert(tz_string)
    )

    # Compute both Supertrend structures along with their respective Inverted Mirror Lines
    st1_line, st1_mirror = _compute_single_st(df, period=CONFIG["ST1"]["PERIOD"], factor=CONFIG["ST1"]["FACTOR"])
    st2_line, st2_mirror = _compute_single_st(df, period=CONFIG["ST2"]["PERIOD"], factor=CONFIG["ST2"]["FACTOR"])

    # --- 3-ZONE CLASSIFIER MATRIX LAYERING ---
    # Using ST1 as our primary engine reference point to isolate channel bounds
    close_arr = df['Close'].to_numpy()
    st_arr = st1_line.to_numpy()
    mirror_arr = st1_mirror.to_numpy()
    
    highest_bound = np.maximum(st_arr, mirror_arr)
    lowest_bound = np.minimum(st_arr, mirror_arr)
    
    # Vectorized sorting layer mapping exactly to your rules
    classifier_conditions = [
        (close_arr > highest_bound),
        (close_arr < lowest_bound)
    ]
    classifier_choices = ['BULL', 'BEAR']
    st_trend_series = pd.Series(
        np.select(classifier_conditions, classifier_choices, default='SIDE'),
        index=df.index
    )

    # CRITICAL DOWNSIDE BACKWARD COMPATIBILITY PROTECTIONS
    df['sma21'] = st1_line
    df['st_line'] = st2_line
    df['sma50'] = st2_line  
    df['ST'] = st1_line
    df['sma_trend_full'] = st_trend_series
    df['ST_Trend'] = st_trend_series
    
    # Hidden helper columns appended so you can pull mirror data tracking downstream if needed
    df['st1_mirror'] = st1_mirror
    df['st2_mirror'] = st2_mirror

    return df


def export_supertrend_json(
    df: pd.DataFrame = None, output_file='../web/webchrtpxy.json'
):
    """Exports and retains legacy key frames alongside requested configuration variables."""
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
    if df is None or df.empty:
        return None
    output = []
    for idx, row in df.iterrows():
        output.append({
            'time': int(idx.timestamp()),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'sma21': float(row['sma21']) if not pd.isna(row['sma21']) else 0.0,
            'st_line': float(row['st_line']) if not pd.isna(row['st_line']) else 0.0,
            'sma50': float(row['sma50']) if not pd.isna(row['sma50']) else 0.0,
            'trend': str(row['ST_Trend'])
        })
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    return output


if __name__ == '__main__':
    print('--- STARTING LIVE PXY UNIFIED EXCLUSIVE MATRIX ENGINE ---')
    processed_df = calculate_supertrend(pd.DataFrame())
    if processed_df is not None and not processed_df.empty:
        target_index = processed_df.index[-1]
        print(f"Timestamp : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(
            f"O:{float(processed_df.at[target_index, 'Open']):.2f}"
            f" H:{float(processed_df.at[target_index, 'High']):.2f}"
            f" L:{float(processed_df.at[target_index, 'Low']):.2f}"
            f" C:{float(processed_df.at[target_index, 'Close']):.2f}"
        )
        print(
            f"ST1 ({CONFIG['ST1']['PERIOD']},{CONFIG['ST1']['FACTOR']}) [sma21]: {float(processed_df.at[target_index, 'sma21']):.2f} | "
            f"ST1 Mirror Line Tracker: {float(processed_df.at[target_index, 'st1_mirror']):.2f}"
        )
        print(f"Aggregated 3-Zone Trend State : {str(processed_df.at[target_index, 'ST_Trend'])}")
        export_supertrend_json(processed_df)
    else:
        print('CRITICAL: Upstream data empty.')
