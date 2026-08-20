"""
Market Data Ingestion and Structural Transformation Pipeline.

This module provides high-performance vectorized operations to ingest financial 
time-series data via Yahoo Finance, apply timezone standardizations, and execute 
isolated mathematical transformations on OHLC pricing structures.
"""

import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from syscnfgpxy import TICKER, OHLC_MODE

# Suppress downcast and indexing warnings from underlying pandas transformations
warnings.simplefilter(action='ignore', category=FutureWarning)

# Target timezone definition for internal market synchronization
TIMEZONE = 'Asia/Kolkata'


def apply_ohlc_transformation(df: pd.DataFrame, mode: int = 1) -> pd.DataFrame:
    """
    Executes isolated, mathematical vector mutations on OHLC columns.

    This function utilizes direct NumPy array views to eliminate pandas series 
    overhead. It provides structural alterations to candlestick geometry to 
    surface alternative trend definitions for statistical trading strategies.

    Parameters
    ----------
    df : pd.DataFrame
        Input historical market data containing standard 'Open', 'High', 
        'Low', and 'Close' columns.
    mode : int, default 1
        Selection flag configuring the mathematical transformation profile:
        - Mode 0: Hyper-Sensitive Close: Weighted heavily toward Close.
        - Mode 1: Raw Pass-Through: Returns unmodified structures.
        - Mode 2: Mid-Body Isolation: Replaces Close with Open-Close average.
        - Mode 3: Range Expansion: Replaces Close with global OHLC average.
        - Mode 4: Algebraic Equilibrium: Replaces Close with solved non-recursive
                  average of Modes 1, 2, 3, and 4.

    Returns
    -------
    pd.DataFrame
        A deep copy of the original DataFrame featuring modified pricing columns.
    """
    if df.empty:
        return df
        
    out = df.copy()
    raw_o = df['Open'].to_numpy()
    raw_h = df['High'].to_numpy()
    raw_l = df['Low'].to_numpy()
    raw_c = df['Close'].to_numpy()
    
    # Mode 0: Hyper-Sensitive Modified Close Candles
    if mode == 0:
        out['Close'] = (raw_o + 2.0 * raw_c) / 3.0

    # Mode 1: Raw Candles (Intentional Pass-Through)
    elif mode == 1:
        pass
        
    # Mode 2: Mid-Body (Only Close changes to OC/2)
    elif mode == 2:
        out['Close'] = (raw_o + raw_c) / 2.0
        
    # Mode 3: Full Range (Only Close changes to OHLC/4)
    elif mode == 3:
        out['Close'] = (raw_o + raw_h + raw_l + raw_c) / 4.0
        
    # Mode 4: Solved Algebraic Average of Modes 1, 2, 3, and 4
    elif mode == 4:
        m1_c = raw_c
        m2_c = (raw_o + raw_c) / 2.0
        m3_c = (raw_o + raw_h + raw_l + raw_c) / 4.0
        
        # Directly assign the mathematically isolated, non-recursive equilibrium point
        out['Close'] = (m1_c + m2_c + m3_c) / 3.0
        
    return out


def fetch_yf_data(period: str = None, interval: str = "1m", target_rows: int = 60) -> pd.DataFrame:
    """
    Ingests market ticks and coordinates temporal/structural transformations.

    Executes a tiered recovery routine searching across increasing historical 
    horizons to secure a valid lookback array size before handing off raw data 
    to the transformation matrix.

    Parameters
    ----------
    period : str, optional
        Initial lookup duration parameter (e.g., "1d", "2d"). If ingestion fails 
        or is omitted, fallbacks trigger automatically.
    interval : str, default "1m"
        Data granular spacing matching yfinance parameters (e.g., "1m", "5m").
    target_rows : int, default 60
        The clean output length requested for down-stream processing.

    Returns
    -------
    pd.DataFrame
        Timezone corrected, transformed data slice bounded exactly to target_rows.
        Returns an empty DataFrame if lookup buffers are starved.
    """
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    buffer_rows = target_rows + 5  # Safety offset to avoid calculation edge-truncation
    
    # Phase 1: Try primary ingestion parameter
    if period is not None:
        try:
            df = ticker_obj.history(period=period, interval=interval)
        except Exception:
            pass
            
    # Phase 2: Cascading fallback sweep if primary target failed or is empty
    if df.empty:
        for search_period in ["5d", "7d", "max"]:
            try:
                df = ticker_obj.history(period=search_period, interval=interval)
                if not df.empty:
                    df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
                    if len(df) >= buffer_rows:
                        break
            except Exception:
                pass
                
    # Validation Gate: Halt processing if window size constraints are violated
    if df.empty or len(df) < buffer_rows:
        return pd.DataFrame()
        
    # Phase 3: Enforce Uniform DateTime Typings
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    # Phase 4: Timezone standardisation pass
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)
        
    # Phase 5: Pass unified historical frame through transformation engine
    processed_df = apply_ohlc_transformation(df, mode=OHLC_MODE)
    
    # Slicing Step: Drop buffer padding, returning exactly requested array bounds
    return processed_df.tail(target_rows)

