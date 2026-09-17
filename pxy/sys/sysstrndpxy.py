import json
import os
import warnings
import numpy as np
import pandas as pd
from syscnfgpxy import TIMEZONE

# ==============================================================================
# 🎛️ GLOBAL MASTER ENGINE SWITCH (Change here to swap logic instantly)
# ==============================================================================
ACTIVE_ENGINE = "TSMA"  # Options: "ST" (Supertrend) or "TSMA" (Pure 7-Period LinReg)
# ==============================================================================

# 🎯 IMPORT THE ORIGINAL ATR VALUE DIRECTLY FROM YOUR UNTOUCHED ENGINE
from syskatrpxy import calculate_atr

warnings.simplefilter(action='ignore', category=FutureWarning)
DEBUG_MODE = False

# ==============================================================================
# 🛠️ FRAMEWORK PARAMETERS CONFIGURATION
# ==============================================================================
CONFIG = {
    "ST1": {
        "PERIOD": 1.0,   # ATR Period synced to Pine Script (atrPeriod)
        "FACTOR": 0.4    # Multiplier synced to Pine Script (multiplier)
    }
}


def _compute_pure_linreg_tsma(df: pd.DataFrame) -> tuple:
    """Computes a pure 7-Period Time Series Linear Regression baseline.
    
    Returns identical line and mirror series to preserve framework compatibility.
    """
    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    open_arr = df['Open'].to_numpy()
    close = df['Close'].to_numpy()

    length = len(df)
    if length == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    # Base transformation cross tracker engine
    m0 = np.where(close >= open_arr, (close + high) / 2.0, (close + low) / 2.0)

    window = 7
    x = np.arange(window)
    x_mean = x.mean()
    x_dev = x - x_mean
    x_var = np.sum(x_dev**2)

    def rolling_linreg(series):
        if len(series) < window:
            return series.copy()
        
        # Vectorized window generation
        windows = np.lib.stride_tricks.sliding_window_view(series, window_shape=window)
        y_means = windows.mean(axis=1, keepdims=True)
        slopes = np.sum((windows - y_means) * x_dev, axis=1) / x_var
        intercepts = y_means.flatten() - slopes * x_mean
        
        # Project the linear trend at current bar (offset 0)
        lr_current = intercepts + slopes * (window - 1)
        return np.concatenate([series[: window - 1], lr_current])

    # 📈 1. Compute Pure 7-Period Linear Regression Line
    tsma_line = rolling_linreg(close)

    # 🎯 KEEP MIRROR AND LINE EXACTLY THE SAME IF USING TSMA MODE
    return pd.Series(tsma_line, index=df.index), pd.Series(tsma_line, index=df.index), pd.Series(m0, index=df.index)


def _compute_single_st(df: pd.DataFrame, period: float, factor: float) -> tuple:
    """Helper to compute PXY Supertrend bands and the mirror line."""
    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    open_arr = df['Open'].to_numpy()
    close = df['Close'].to_numpy()

    length = len(df)
    if length == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    m0 = np.where(close >= open_arr, (close + high) / 2.0, (close + low) / 2.0)
    src = (high + low) / 2.0  
    
    atr = calculate_atr(df).to_numpy()

    basic_upper = src + (factor * atr)
    basic_lower = src - (factor * atr)

    final_upper = np.zeros(length)
    final_lower = np.zeros(length)
    supertrend = np.zeros(length)
    mirror_line = np.zeros(length)
    st_trend = np.ones(length)  

    anchor_price = float(src[0]) if length > 0 else 0.0

    for i in range(length):
        if i == 0:
            final_upper[i] = basic_upper[i]
            final_lower[i] = basic_lower[i]
            supertrend[i] = final_upper[i]
            st_trend[i] = -1 
            mirror_line[i] = anchor_price - (supertrend[i] - anchor_price)
            continue

        prev_upper = final_upper[i - 1]
        prev_lower = final_lower[i - 1]
        prev_trend = st_trend[i - 1]

        if src[i] < prev_upper:
            final_upper[i] = min(basic_upper[i], prev_upper)
        else:
            final_upper[i] = basic_upper[i]

        if src[i] > prev_lower:
            final_lower[i] = max(basic_lower[i], prev_lower)
        else:
            final_lower[i] = basic_lower[i]

        if prev_trend == -1 and m0[i] > prev_upper:  
            current_trend = 1
            anchor_price = float(src[i])
        elif prev_trend == 1 and m0[i] < prev_lower:  
            current_trend = -1
            anchor_price = float(src[i])
        else:
            current_trend = prev_trend

        st_trend[i] = current_trend
        stLine = final_lower[i] if current_trend == 1 else final_upper[i]
        supertrend[i] = stLine

        st_distance_from_anchor = stLine - anchor_price
        mirror_line[i] = anchor_price - st_distance_from_anchor

    return pd.Series(supertrend, index=df.index), pd.Series(mirror_line, index=df.index), pd.Series(m0, index=df.index)


def get_market_trend(df: pd.DataFrame) -> str:
    """Evaluates raw data frame layouts via intermediate calculations."""
    if df is None or df.empty or len(df) < 1:
        return 'SIDE'

    if ACTIVE_ENGINE == "TSMA":
        st_line, _, _ = _compute_pure_linreg_tsma(df)
        
        # 🎯 DIRECTLY COMPARE LATEST PRICE WITH PURE LINREG TSMA LINE FOR BULL/BEAR
        close_curr = float(df['Close'].iloc[-1])
        tsma_curr = float(st_line.iloc[-1])
        
        if close_curr > tsma_curr:
            return 'BULL'
        elif close_curr < tsma_curr:
            return 'BEAR'
        else:
            return 'SIDE'
            
    else:
        st_line, mirror_line, m0_series = _compute_single_st(
            df, period=CONFIG["ST1"]["PERIOD"], factor=CONFIG["ST1"]["FACTOR"]
        )
        
        m0_curr = float(m0_series.iloc[-1])
        st_curr = float(st_line.iloc[-1])
        mirror_curr = float(mirror_line.iloc[-1])
        highest_line = max(st_curr, mirror_curr)
        lowest_line = min(st_curr, mirror_curr)

        if m0_curr > highest_line:
            return 'BULL'
        elif m0_curr < lowest_line:
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

    if ACTIVE_ENGINE == "TSMA":
        st1_line, st1_mirror, _ = _compute_pure_linreg_tsma(df)
        tsma_arr = st1_line.to_numpy()
        close_arr = df['Close'].to_numpy()
        
        # 🎯 VECTORIZED DIRECT CLOSE VS PURE LINREG TSMA COMPARISON FOR MASTER MATRIX
        classifier_conditions = [
            (close_arr > tsma_arr),
            (close_arr < tsma_arr)
        ]
    else:
        st1_line, st1_mirror, m0_series = _compute_single_st(df, period=CONFIG["ST1"]["PERIOD"], factor=CONFIG["ST1"]["FACTOR"])
        st_arr = st1_line.to_numpy()
        mirror_arr = st1_mirror.to_numpy()
        m0_arr = m0_series.to_numpy()
        highest_arr = np.maximum(st_arr, mirror_arr)
        lowest_arr = np.minimum(st_arr, mirror_arr)
        
        classifier_conditions = [
            (m0_arr > highest_arr),
            (m0_arr < lowest_arr)
        ]
        
    classifier_choices = ['BULL', 'BEAR']
    st_trend_series = pd.Series(
        np.select(classifier_conditions, classifier_choices, default='SIDE'),
        index=df.index
    )

    # Map variables cleanly to dataframe matrices
    df['st_line'] = st1_line           
    df['st_mirror'] = st1_mirror       
    df['ST_Trend'] = st_trend_series   
    
    # Legacy routing
    df['ST'] = st1_line                
    df['st1_mirror'] = st1_mirror      

    return df


def export_supertrend_json(
    df: pd.DataFrame = None, output_file='../web/webchrtpxy.json'
):
    """Exports structured historical data: OHLC (for candles), st_line + trend
    (for coloring), and mirror_line (always neutral)."""
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
    if df is None or df.empty:
        return None

    output = []
    for idx, row in df.iterrows():
        output.append({
            'time': int(idx.timestamp()),
            'open': float(row['Open']) if not pd.isna(row['Open']) else 0.0,
            'high': float(row['High']) if not pd.isna(row['High']) else 0.0,
            'low': float(row['Low']) if not pd.isna(row['Low']) else 0.0,
            'close': float(row['Close']),
            'st_line': float(row['st_line']) if not pd.isna(row['st_line']) else 0.0,
            'mirror_line': float(row['st_mirror']) if not pd.isna(row['st_mirror']) else 0.0,
            'trend': str(row.get('ST_Trend', 'SIDE')) if not pd.isna(row.get('ST_Trend', 'SIDE')) else 'SIDE'
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
        current_trend = get_market_trend(processed_df)
        
        print(f"Timestamp : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Price Line (Close): {float(processed_df.at[target_index, 'Close']):.2f}")
        print(
            f"ST1 Line ({CONFIG['ST1']['PERIOD']},{CONFIG['ST1']['FACTOR']}): {float(processed_df.at[target_index, 'st_line']):.2f} | "
            f"Mirror Line Tracker: {float(processed_df.at[target_index, 'st_mirror']):.2f}"
        )
        print(f"Current Market Trend State : {current_trend}")
        
        export_supertrend_json(processed_df)
    else:
        print('CRITICAL: Upstream data empty.')


