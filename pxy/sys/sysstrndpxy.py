# sysstrndpxy.py
import json
import os
import warnings
import pandas as pd

import syscnfgpxy
from syssmapxy import calculate_moving_average
from sysdtstpxy import calculate_supertrend as calculate_entry_supertrend
from sysdtstpxy import get_market_trend as get_entry_market_trend

TIMEZONE = syscnfgpxy.SYSCNFGPXY_TIMEZONE

warnings.simplefilter(action='ignore', category=FutureWarning)

# ==============================================================================
# 🎛️ MASTER CONFIGURATION LAYER (PXY Universal Framework Parameters)
# ==============================================================================
def get_market_trend(df: pd.DataFrame) -> str:
    """Return the same configured Supertrend classification used for entry."""
    if df is None or df.empty or len(df) < 2:
        return 'SIDE'
    return get_entry_market_trend(df)


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate chart Supertrend with the exact settings and math used for entries."""
    if df is None:
        return pd.DataFrame()
    if df.empty:
        from sysdtafpxy import fetch_yf_data
        try:
            raw_df = fetch_yf_data(period='3d', interval='1m')
            if raw_df is not None and not raw_df.empty: df = raw_df.copy()
        except Exception:
            df = df.copy()

    if df.empty:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    tz_string = str(TIMEZONE)
    df = df.tz_convert(tz_string) if df.index.tz is not None else df.tz_localize('UTC').tz_convert(tz_string)

    df = calculate_entry_supertrend(df)

    df['ST'] = df['st_line']
    df['st1_mirror'] = df['st_mirror']
    df['sma_50'] = calculate_moving_average(df['Close'], period=50, variant="SMA")
    df['tsma_50'] = calculate_moving_average(df['Close'], period=50, variant="TSMA")

    return df


def export_supertrend_json(df: pd.DataFrame = None, output_file='../web/webchrtpxy.json'):
    """Exports structured historical data for chart visualizations."""
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
    if df is None or df.empty:
        return None

    output = []
    for idx, row in df.iterrows():
        st_val = float(row['st_line']) if not pd.isna(row['st_line']) else 0.0
        mirror_val = float(row['st_mirror']) if not pd.isna(row['st_mirror']) else 0.0
        sma_val = float(row['sma_50']) if not pd.isna(row.get('sma_50')) else None
        tsma_val = float(row['tsma_50']) if not pd.isna(row.get('tsma_50')) else None

        output.append({
            'time': int(idx.timestamp()),
            'open': float(row['Open']) if not pd.isna(row['Open']) else 0.0,
            'high': float(row['High']) if not pd.isna(row['High']) else 0.0,
            'low': float(row['Low']) if not pd.isna(row['Low']) else 0.0,
            'close': float(row['Close']),
            'st_line': st_val,
            'mirror_line': mirror_val,
            'sma50': sma_val,
            'tsma50': tsma_val,
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
            f"ST1 Line (Combo Avg Line): {float(processed_df.at[target_index, 'st_line']):.2f} | "
            f"Mirror Line Tracker: {float(processed_df.at[target_index, 'st_mirror']):.2f}"
        )
        print(f"Current Market Trend State : {current_trend}")
        
        export_supertrend_json(processed_df)
    else:
        print('CRITICAL: Upstream data empty.')
