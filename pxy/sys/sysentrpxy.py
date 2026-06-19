"""""
===============================================================================
PXY OPTION ROUTING ENGINE: TWO-PIPE DIRECT MARKET FILTER (BULL/BEAR ONLY)
===============================================================================
Operational Matrix:
- EXIT PIPE (Unfiltered): Exactly as received from Upstream (BULL/BEAR)
- ENTRY PIPE (Filtered): 
    - MKT_SIGNAL: BULL -> ATMBUY
    - MKT_SIGNAL: BEAR -> ATMSELL
    - Otherwise        -> NONE
===============================================================================
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# =============================================================================
# EXCLUSIVE STANDALONE PLATFORM CONFIGURATION (NO EXTERNAL DEPENDENCIES)
# =============================================================================
TICKER = "^NSEI"             # Target trading asset (NIFTY 50 Official Yahoo Ticker)
INTERVAL = "1m"            # Real-time streaming bar chart interval
PERIOD = "5d"              # Historical data fetch footprint buffer
TIMEZONE = "Asia/Kolkata"  # Target market localized coordinate string for NSE India

# 1. RUNTIME ENGINE SAME-DIRECTORY PATH ALIGNMENT
local_dir = os.path.dirname(os.path.abspath(__file__))
if local_dir not in sys.path:
    sys.path.insert(0, local_dir)


def calculate_tsma_7(series):
    """Computes a 7-period Time Series Moving Average (Linear Regression Curve)

    matching the mathematical logic of TradingView's ta.linreg(close, 7, 0).
    """
    length = 7
    if len(series) < length:
        return pd.Series(np.nan, index=series.index)
        
    # Pre-calculate linear regression multipliers for least squares matrix
    x = np.arange(length)
    x_mean = x.mean()
    x_deviations = x - x_mean
    var_x = (x_deviations ** 2).sum()

    def get_last_fitted_value(window):
        if len(window) < length:
            return np.nan
        y = np.array(window)
        y_mean = y.mean()
        # Calculate slope (m) and intercept (b)
        slope = (x_deviations * (y - y_mean)).sum() / var_x
        intercept = y_mean - slope * x_mean
        return intercept + slope * (length - 1)

    # Apply rolling linear regression curve lookup
    return series.rolling(window=length).apply(get_last_fitted_value, raw=True)


def get_entry_signal(df=None):
    """Calculates a 7-period TSMA on Close data to define trend vectors.

    Enforces exclusive conditional checks without a default baseline assumption.
    """
    # 2. TARGET DATAFRAME HANDLING & DIRECT AUTO-FETCH IF NONE PASSED
    if df is None or df.empty:
        try:
            ticker_obj = yf.Ticker(TICKER)
            target_df = ticker_obj.history(period=PERIOD, interval=INTERVAL)
            if not target_df.empty:
                target_df.dropna(inplace=True)
                if target_df.index.tz is None:
                    target_df = target_df.tz_localize('UTC').tz_convert(TIMEZONE)
                else:
                    target_df = target_df.tz_convert(TIMEZONE)
            else:
                return "NONE", "NONE"
        except Exception:
            return "NONE", "NONE"
    else:
        target_df = df

    # Double check final structure requirements before starting calculation
    if target_df.empty or len(target_df) < 8 or 'Close' not in target_df.columns:
        return "NONE", "NONE"

    try:
        # 3. COMPUTE 7-PERIOD TSMA ENGINE VALUE
        close_series = target_df['Close']
        tsma_values = calculate_tsma_7(close_series)
        
        # Pull latest completed candle metrics (n-1 row index alignment)
        current_close = float(close_series.iloc[-1])
        current_tsma = float(tsma_values.iloc[-1])

        # 4. EXCLUSIVE CONDITIONAL MATCHING LAYER
        if pd.isna(current_tsma):
            raw_signal = "NONE"
        elif current_close > current_tsma:
            raw_signal = "BULL"
        elif current_close < current_tsma:
            raw_signal = "BEAR"
        else:
            raw_signal = "NONE"

        # 5. UNFILTERED CASCADED EXIT PIPE
        exit_sig = raw_signal

        # 6. ENTRY PIPE: EXCLUSIVE ATM REWRITE CONVERSION MATRIX
        if raw_signal == "BULL":
            final_signal = "ATMBUY"
        elif raw_signal == "BEAR":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"

    except Exception:
        final_signal = "NONE"
        exit_sig = "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    print(f"--- STARTING STANDALONE PXY ENGINE FOR Ticker: {TICKER} ---")
    
    # Run signal execution using autonomous internal data download loop
    final_route, cascaded_exit = get_entry_signal(df=None)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY : {final_route}")
    print(f"-> CASCADED EXIT: {cascaded_exit}\n")

