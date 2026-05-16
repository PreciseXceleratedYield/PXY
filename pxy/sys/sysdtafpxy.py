import os
import warnings
from datetime import datetime, time
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE
import pytz

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# Track if raw dump has run for this session
_RAW_DUMP_DONE = False

def dump_raw_json_in_window(ticker_obj, period="1d", interval="1m"):
    """Dumps raw JSON to parent directory if within the time window on first fetch."""
    global _RAW_DUMP_DONE
    if _RAW_DUMP_DONE:
        return

    # Check IST time window (15:45 PM IST to 09:14 AM IST next day)
    ist_tz = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist_tz).time()
    start_time = time(15, 45)
    end_time = time(9, 14)

    # Strictly execute only inside this specific window
    if start_time <= now_ist <= end_time:
        try:
            # Fetch absolute raw fast info/history JSON
            raw_data = ticker_obj.history(period=period, interval=interval)
            
            # Setup paths
            script_directory = os.path.dirname(os.path.abspath(__file__))
            parent_directory = os.path.dirname(script_directory)
            base_name = os.path.splitext(os.path.basename(__file__))[0]
            target_export_path = os.path.join(parent_directory, f"{base_name}.json")
            
            # Dump to JSON
            raw_data.to_json(target_export_path, date_format='iso', orient='split')
            _RAW_DUMP_DONE = True
        except Exception as e:
            print(f"RAW_JSON_DUMP_ERROR | {e}")

def get_heikin_ashi_ohlc(o, h, l, c):
    """Generates pure Heikin-Ashi smooth trend OHLC matrices"""
    ha_c = (o + h + l + c) / 4
    ha_o = np.zeros_like(o)
    ha_o[0] = (o[0] + c[0]) / 2
    for i in range(1, len(o)):
        ha_o[i] = (ha_o[i-1] + ha_c[i-1]) / 2
    ha_h = np.maximum(h, np.maximum(ha_o, ha_c))
    ha_l = np.minimum(l, np.minimum(ha_o, ha_c))
    return ha_o, ha_h, ha_l, ha_c

def get_open_close_median_ohlc(o, c):
    """Generates flat candle Open-Close Midpoint OHLC matrices (oc/2)"""
    oc2 = (o + c) / 2
    return oc2, oc2, oc2, oc2

def get_momentum_ohlc(c):
    """Generates shift momentum OHLC matrices using prior close boundaries (c1 c0)"""
    c1 = np.empty_like(c)
    c1[0] = c[0]
    c1[1:] = c[:-1]
    return c1, c, c1, c

def apply_ohlc_transformation(df, mode=1):
    """Transforms raw arrays into distinct, complete structural OHLC formats"""
    if df.empty: return df
    o = df['Open'].to_numpy()
    h = df['High'].to_numpy()
    l = df['Low'].to_numpy()
    c = df['Close'].to_numpy()
    if mode == 1:
        return df
    elif mode == 2:
        df['Open'], df['High'], df['Low'], df['Close'] = get_heikin_ashi_ohlc(o, h, l, c)
    elif mode == 3:
        df['Open'], df['High'], df['Low'], df['Close'] = get_open_close_median_ohlc(o, c)
    elif mode == 4:
        df['Open'], df['High'], df['Low'], df['Close'] = get_momentum_ohlc(c)
    elif mode == 5:
        ha_o, ha_h, ha_l, ha_c = get_heikin_ashi_ohlc(o, h, l, c)
        oc2_o, oc2_h, oc2_l, oc2_c = get_open_close_median_ohlc(o, c)
        c1c0_o, c1c0_h, c1c0_l, c1c0_c = get_momentum_ohlc(c)
        df['Open'] = (o + ha_o + oc2_o + c1c0_o) / 4
        df['High'] = (h + ha_h + oc2_h + c1c0_h) / 4
        df['Low'] = (l + ha_l + oc2_l + c1c0_l) / 4
        df['Close'] = (c + ha_c + oc2_c + c1c0_c) / 4
    else:
        print(f"SYSTEM_WARNING | Mode {mode} unrecognized. Defaulting to Raw OHLC.")
    return df

def write_matrix_to_parent_csv(df):
    """Saves data into the parent directory using the script filename string"""
    try:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        parent_directory = os.path.dirname(script_directory)
        base_name = os.path.splitext(os.path.basename(__file__))[0]
        base_filename = base_name + ".csv"
        target_export_path = os.path.join(parent_directory, base_filename)
        df.to_csv(target_export_path, index=True)
    except Exception as e:
        print(f"CSV_EXPORT_ERROR | Write operation failure: {e}")

def fetch_yf_data(period="1d", interval="1m", target_rows=52):
    """
    PERMANENT 52-ROW STRUCTURE PROCESSING ENGINE
    """
    try:
        ticker_obj = yf.Ticker(TICKER)
        
        # Intercept here for pure raw dump on first fetch
        dump_raw_json_in_window(ticker_obj, period, interval)
        
        df = ticker_obj.history(period=period, interval=interval)
        if df.empty:
            print("WARNING: Yahoo Finance data engine returned an empty frame.")
            return pd.DataFrame()
        df.dropna(inplace=True)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df = df.tz_localize('UTC').tz_convert(TIMEZONE)
        else:
            df = df.tz_convert(TIMEZONE)
        live_rows = len(df)
        if live_rows < target_rows:
            needed_rows = target_rows - live_rows
            first_bar = df.iloc[0]
            base_time = df.index[0]
            padded_timestamps = [base_time - pd.Timedelta(minutes=i) for i in range(needed_rows, 0, -1)]
            padding_df = pd.concat([first_bar.to_frame().T] * needed_rows, ignore_index=True)
            padding_df.index = padded_timestamps
            df = pd.concat([padding_df, df])
        else:
            df = df.tail(target_rows)
        df = df.copy()
        processed_df = apply_ohlc_transformation(df, mode=OHLC_MODE)
        write_matrix_to_parent_csv(processed_df)
        return processed_df
    except Exception as e:
        print(f"YFINANCE_ENGINE_FAILURE | {e}")
        return pd.DataFrame()

def get_latest_data():
    """Returns the most recent live completed row using active config files parameters"""
    return fetch_yf_data().tail(1)

if __name__ == "__main__":
    print(f"=== PROCESSING RUNNING | ENGINE TARGET TICKER: {TICKER} ===")
    print(f"=== CURRENTLY ENFORCED DATA TRANSFORMATION MODE: {OHLC_MODE} ===")
    output_df = fetch_yf_data()
    if not output_df.empty:
        print(f"ENGINE_RUN_SUCCESS | Total Data Frame Sizing Bounds: {output_df.shape}")


