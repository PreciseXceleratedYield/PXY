import json
import os
import warnings
import numpy as np
import pandas as pd
from syscnfgpxy import TIMEZONE

warnings.simplefilter(action='ignore', category=FutureWarning)
DEBUG_MODE = False

# ==============================================================================
# 🎛️ MASTER CONFIGURATION LAYER (PXY Universal Framework Parameters)
# ==============================================================================
CONFIG = {
    "ST1": {
        "PERIOD": 3.0,   # ATR Period synced to Pine Script
        "FACTOR": 1.4    # Multiplier synced to Pine Script
    }
}
# ==============================================================================


def _compute_single_st(df: pd.DataFrame, period: float, factor: float) -> tuple:
    """Helper to compute standard Supertrend bands and the absolute inverse mirror line.
    
    Fixed tracking engine preventing bi-directional band jumping.
    """
    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    close = df['Close'].to_numpy()

    length = len(df)
    if length == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    # Base source uses hl2 midpoint average natively
    src = (high + low) / 2.0

    # --- CORRECTED TRUE RANGE COMPUTATION ---
    tr1 = high - low
    close_shifted = df['Close'].shift(1).to_numpy()
    if length > 0:
        close_shifted[0] = close[0]  # Safe seed allocation

    tr2 = np.abs(high - close_shifted)
    tr3 = np.abs(low - close_shifted)
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # Linear rolling simple moving average matching standard script indicators
    atr = pd.Series(tr, index=df.index).rolling(window=int(period), min_periods=1).mean().to_numpy()

    basic_upper = src + (factor * atr)
    basic_lower = src - (factor * atr)

    final_upper = np.zeros(length)
    final_lower = np.zeros(length)
    supertrend = np.zeros(length)
    mirror_line = np.zeros(length)
    st_trend = []

    anchor_price = src[0] if length > 0 else 0.0

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

        # --- CORRECTED TRAILING BAND RETENTION LOGIC ---
        # Upper band can only move down during a downtrend unless breached
        if basic_upper[i] < prev_upper or close[i - 1] > prev_upper:
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = prev_upper

        # Lower band can only move up during an uptrend unless breached
        if basic_lower[i] > prev_lower or close[i - 1] < prev_lower:
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = prev_lower

        # --- EVALUATE TREND SWITCH MATRIX ---
        if prev_trend == 'BEAR':
            if close[i] > final_upper[i]:
                st_trend.append('BULL')
                supertrend[i] = final_lower[i]
                anchor_price = src[i]  # Reset spacetime anchor on trend shift
            else:
                st_trend.append('BEAR')
                supertrend[i] = final_upper[i]
        else:
            if close[i] < final_lower[i]:
                st_trend.append('BEAR')
                supertrend[i] = final_upper[i]
                anchor_price = src[i]  # Reset spacetime anchor on trend shift
            else:
                st_trend.append('BULL')
                supertrend[i] = final_lower[i]

        # Compute the Spacetime Anchor Inverted Mirror Line
        st_distance_from_anchor = supertrend[i] - anchor_price
        mirror_line[i] = anchor_price - st_distance_from_anchor

    return pd.Series(supertrend, index=df.index), pd.Series(mirror_line, index=df.index)


def get_market_trend(df: pd.DataFrame) -> str:
    """
    Evaluates raw data frame layouts via intermediate calculations.
    Returns: 'BULL', 'BEAR', or 'SIDE' based on the Three-State Market Filter layout.
    """
    if df is None or df.empty or len(df) < 2:
        return 'SIDE'

    st_line, mirror_line = _compute_single_st(df, period=CONFIG["ST1"]["PERIOD"], factor=CONFIG["ST1"]["FACTOR"])
    
    close_curr = float(df['Close'].iloc[-1])
    st_curr = float(st_line.iloc[-1])
    mirror_curr = float(mirror_line.iloc[-1])
    
    highest_line = max(st_curr, mirror_curr)
    lowest_line = min(st_curr, mirror_curr)

    if close_curr > highest_line:
        return 'BULL'
    elif close_curr < lowest_line:
        return 'BEAR'
    else:
        return 'SIDE'


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates Universal Supertrend Master Matrix and returns structural states."""
    if df.empty:
        from sysdtafpxy import fetch_yf_data
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
    if df.index.tz is not None:
        df = df.tz_convert(tz_string)
    else:
        df = df.tz_localize('UTC').tz_convert(tz_string)

    st1_line, st1_mirror = _compute_single_st(df, period=CONFIG["ST1"]["PERIOD"], factor=CONFIG["ST1"]["FACTOR"])

    close_arr = df['Close'].to_numpy()
    st_arr = st1_line.to_numpy()
    mirror_arr = st1_mirror.to_numpy()
    
    highest_arr = np.maximum(st_arr, mirror_arr)
    lowest_arr = np.minimum(st_arr, mirror_arr)
    
    # Complete Three-State Vectorized Evaluation Engine
    classifier_conditions = [
        (close_arr > highest_arr),
        (close_arr < lowest_arr)
    ]
    classifier_choices = ['BULL', 'BEAR']
    st_trend_series = pd.Series(
        np.select(classifier_conditions, classifier_choices, default='SIDE'),
        index=df.index
    )

    # ==========================================================================
    # ⚡ EXPLICIT MAP REFLECTION CORRECTIONS
    # ==========================================================================
    df['sma21'] = st1_mirror           # Map sma21 explicitly to the Inverse Mirror Line
    df['st_line'] = st1_line           # Map st_line explicitly to original Supertrend
    df['ST'] = st1_line                # Map ST explicitly to original Supertrend
    
    # Structural keys preserved for legacy backend mapping compatibilities
    df['sma50'] = st1_line             
    df['sma_trend_full'] = st_trend_series
    df['ST_Trend'] = st_trend_series
    df['st1_mirror'] = st1_mirror
    df['st2_mirror'] = st1_mirror 

    return df



def export_supertrend_json(
    df: pd.DataFrame = None, output_file='../web/webchrtpxy.json'
):
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
    from sysdtafpxy import fetch_yf_data
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
