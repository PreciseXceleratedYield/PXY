import json
import os
import warnings
from syscnfgpxy import TIMEZONE
from sysdtafpxy import fetch_yf_data
import pandas as pd

warnings.simplefilter(action='ignore', category=FutureWarning)

DEBUG_MODE = False


def _compute_single_st(df: pd.DataFrame, period: float, factor: float) -> tuple:
    """Helper to compute standard Supertrend bands and trend vectors."""
    high = df['High']
    low = df['Low']
    close = df['Close']

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Wilder's Smoothing via EWM
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()

    hl2 = (high + low) / 2
    basic_upper = hl2 + (factor * atr)
    basic_lower = hl2 - (factor * atr)

    final_upper = pd.Series(index=df.index, dtype='float64')
    final_lower = pd.Series(index=df.index, dtype='float64')
    supertrend = pd.Series(index=df.index, dtype='float64')
    st_trend = pd.Series(index=df.index, dtype='object')

    for i in range(len(df)):
        if i == 0:
            final_upper.iloc[i] = basic_upper.iloc[i]
            final_lower.iloc[i] = basic_lower.iloc[i]
            supertrend.iloc[i] = final_upper.iloc[i]
            st_trend.iloc[i] = 'BEAR'
            continue

        prev_upper = final_upper.iloc[i - 1]
        prev_lower = final_lower.iloc[i - 1]
        prev_trend = st_trend.iloc[i - 1]

        if basic_upper.iloc[i] < prev_upper or close.iloc[i - 1] > prev_upper:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = prev_upper

        if basic_lower.iloc[i] > prev_lower or close.iloc[i - 1] < prev_lower:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = prev_lower

        if prev_trend == 'BEAR':
            if close.iloc[i] > final_upper.iloc[i]:
                st_trend.iloc[i] = 'BULL'
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                st_trend.iloc[i] = 'BEAR'
                supertrend.iloc[i] = final_upper.iloc[i]
        else:
            if close.iloc[i] < final_lower.iloc[i]:
                st_trend.iloc[i] = 'BEAR'
                supertrend.iloc[i] = final_upper.iloc[i]
            else:
                st_trend.iloc[i] = 'BULL'
                supertrend.iloc[i] = final_lower.iloc[i]

    return supertrend, st_trend


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates Dual Supertrends (7,3 and 3,7).
    
    If both trends match, outputs BULL/BEAR, otherwise SIDE.
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

    # Compute both Supertrends
    st1_line, st1_trend = _compute_single_st(df, period=7.0, factor=3.0)
    st2_line, st2_trend = _compute_single_st(df, period=3.0, factor=7.0)

    # Determine aligned matrices (BULL/BEAR if agreed, else SIDE)
    final_trend = []
    for t1, t2 in zip(st1_trend, st2_trend):
        if t1 == t2:
            final_trend.append(t1)
        else:
            final_trend.append('SIDE')

    # Mapping lines requested for dump allocation
    df['sma21'] = st1_line       # Supertrend (7, 3) mapped as requested
    df['st_line'] = st2_line     # Supertrend (3, 7) mapped as requested
    df['ST_Trend'] = pd.Series(final_trend, index=df.index)

    return df


def export_supertrend_json(
    df: pd.DataFrame = None, output_file='../web/webchrtpxy.json'
):
    """Exports custom dump configurations mapping sma21 and st_line lines."""
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
    if df is None or df.empty:
        return None
    output = []
    for idx, row in df.iterrows():
        output.append({
            'time': str(idx),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(row['Close']),
            'sma21': float(row['sma21']) if not pd.isna(row['sma21']) else 0.0,
            'st_line': float(row['st_line']) if not pd.isna(row['st_line']) else 0.0,
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
            f"ST (7,3) [sma21]: {float(processed_df.at[target_index, 'sma21']):.2f} | "
            f"ST (3,7) [st_line]: {float(processed_df.at[target_index, 'st_line']):.2f}"
        )
        print(f"Aggregated Trend State : {str(processed_df.at[target_index, 'ST_Trend'])}")
        export_supertrend_json(processed_df)
    else:
        print('CRITICAL: Upstream data empty.')



