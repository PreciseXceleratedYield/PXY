# sysstrndpxy.py
import json
import os
import sys
import warnings
import numpy as np
import pandas as pd
from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE as TIMEZONE,
    SYSSTRNDPXY_COMBO_SMA_PERIOD,
    SYSSTRNDPXY_COMBO_ST_FACTOR,
    SYSSTRNDPXY_COMBO_ST_PERIOD,
    SYSSTRNDPXY_SMA_PERIOD,
    SYSSTRNDPXY_ST1_FACTOR,
    SYSSTRNDPXY_ST1_PERIOD,
    SYSSTRNDPXY_VARIANT,
)

# 🛡️ DEFENSIVE IMPORTS ROUTING MATH DIRECTLY TO THE CALCULATION ENGINE
try:
    from systrcalpxy import _compute_single_st, _compute_combo_force, _compute_sma_trend
except ImportError as e:
    # No fake trend: zeros would read as SIDE and live trading would carry on copying the candle.
    # Every call now raises, and sysentrpxy turns that into NONE/NONE (no entry, no exit key).
    print(f"🚨 CRITICAL: Cannot locate 'systrcalpxy.py' ({e}). Trend engine disabled.", file=sys.stderr)
    _IMPORT_ERR = str(e)

    def _engine_down(*args, **kwargs):
        raise RuntimeError(f"systrcalpxy unavailable ({_IMPORT_ERR}); refusing to fake a trend.")

    _compute_single_st = _compute_sma_trend = _compute_combo_force = _engine_down

warnings.simplefilter(action='ignore', category=FutureWarning)
DEBUG_MODE = False

# ==============================================================================
# 🎛️ MASTER CONFIGURATION LAYER (PXY Universal Framework Parameters)
# ==============================================================================
def get_market_trend(df: pd.DataFrame) -> str:
    """Evaluates raw data frame layouts via intermediate calculations handles."""
    if df is None or df.empty or len(df) < 2:
        return 'SIDE'

    variant = SYSSTRNDPXY_VARIANT.upper()
    
    if variant == "COMBO_FORCE":
        min_required = max(SYSSTRNDPXY_COMBO_ST_PERIOD, SYSSTRNDPXY_COMBO_SMA_PERIOD)
        if len(df) < min_required:
            return 'SIDE'
        _, trend_series = _compute_combo_force(
            df, 
            st_period=SYSSTRNDPXY_COMBO_ST_PERIOD,
            st_factor=SYSSTRNDPXY_COMBO_ST_FACTOR,
            sma_period=SYSSTRNDPXY_COMBO_SMA_PERIOD,
        )
        return str(trend_series.iloc[-1])

    if variant == "SMA50":
        _, trend_series = _compute_sma_trend(df, SYSSTRNDPXY_SMA_PERIOD)
        return str(trend_series.iloc[-1])

    st_line, mirror_line, m0_series, raw_trend_series = _compute_single_st(
        df, period=SYSSTRNDPXY_ST1_PERIOD, factor=SYSSTRNDPXY_ST1_FACTOR
    )
    if variant == "SINGLE":
        return 'BULL' if raw_trend_series.iloc[-1] == 1 else 'BEAR'
        
    m0_curr, st_curr, mirror_curr = float(m0_series.iloc[-1]), float(st_line.iloc[-1]), float(mirror_line.iloc[-1])
    highest_line, lowest_line = max(st_curr, mirror_curr), min(st_curr, mirror_curr)
    if m0_curr > highest_line: return 'BULL'
    elif m0_curr < lowest_line: return 'BEAR'
    return 'SIDE'


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates Universal Supertrend Master Matrix and returns structural states."""
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

    variant = SYSSTRNDPXY_VARIANT.upper()

    if variant == "COMBO_FORCE":
        min_required = max(SYSSTRNDPXY_COMBO_ST_PERIOD, SYSSTRNDPXY_COMBO_SMA_PERIOD)
        if len(df) < min_required:
            st1_line = pd.Series(df['Close'], index=df.index)
            st1_mirror = st1_line
            st_trend_series = pd.Series("SIDE", index=df.index)
        else:
            st1_line, st_trend_series = _compute_combo_force(
                df, 
                st_period=SYSSTRNDPXY_COMBO_ST_PERIOD,
                st_factor=SYSSTRNDPXY_COMBO_ST_FACTOR,
                sma_period=SYSSTRNDPXY_COMBO_SMA_PERIOD,
            )
            st1_mirror = st1_line
            
    elif variant == "SMA50":
        st1_line, st_trend_series = _compute_sma_trend(df, SYSSTRNDPXY_SMA_PERIOD)
        st1_mirror = st1_line
    else:
        st1_line, st1_mirror, m0_series, raw_trend_series = _compute_single_st(
            df, period=SYSSTRNDPXY_ST1_PERIOD, factor=SYSSTRNDPXY_ST1_FACTOR
        )
        if variant == "SINGLE":
            st_trend_series = pd.Series(np.where(raw_trend_series == 1, 'BULL', 'BEAR'), index=df.index)
        else:
            st_arr, mirror_arr, m0_arr = st1_line.to_numpy(), st1_mirror.to_numpy(), m0_series.to_numpy()
            highest_arr, lowest_arr = np.maximum(st_arr, mirror_arr), np.minimum(st_arr, mirror_arr)
            st_trend_series = pd.Series(np.select([m0_arr > highest_arr, m0_arr < lowest_arr], ['BULL', 'BEAR'], default='SIDE'), index=df.index)

    # Clean legacy dashboard field overrides to prevent exceptions
    df['st_line'] = st1_line           
    df['st_mirror'] = st1_mirror       
    df['ST_Trend'] = st_trend_series   
    df['ST'] = st1_line                
    df['st1_mirror'] = st1_mirror      

    return df


def export_supertrend_json(df: pd.DataFrame = None, output_file='../web/webchrtpxy.json'):
    """Exports structured historical data for chart visualizations."""
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
    if df is None or df.empty:
        return None

    output = []
    variant = SYSSTRNDPXY_VARIANT.upper()
    is_single_or_flat = variant in ("SINGLE", "SMA50", "COMBO_FORCE")

    for idx, row in df.iterrows():
        st_val = float(row['st_line']) if not pd.isna(row['st_line']) else 0.0
        mirror_val = st_val if is_single_or_flat else (float(row['st_mirror']) if not pd.isna(row['st_mirror']) else 0.0)

        output.append({
            'time': int(idx.timestamp()),
            'open': float(row['Open']) if not pd.isna(row['Open']) else 0.0,
            'high': float(row['High']) if not pd.isna(row['High']) else 0.0,
            'low': float(row['Low']) if not pd.isna(row['Low']) else 0.0,
            'close': float(row['Close']),
            'st_line': st_val,
            'mirror_line': mirror_val,
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
