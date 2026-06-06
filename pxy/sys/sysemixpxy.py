import pandas as pd
import numpy as np
from colorama import Fore, Style, init

# Direct Module Imports from your custom system architecture files
from sysdtafpxy import fetch_yf_data
from syspwerpxy import get_ce_pe_power
from syskatrpxy import calculate_atr, calculate_dynamic_k

# Initialize terminal visual formats
init(autoreset=True)
TOTAL_WIDTH = 42

def get_live_matrix_signal() -> str:
    """
    Downloads transformed data, parses 13 isolated strategy pipelines,
    and returns ONLY the final active decisive string signal: 'BUY', 'SELL', or 'NONE'.
    """
    try:
        # 1. Fetch live transformed data frame from your sysdtafpxy engine
        df = fetch_yf_data()
        if df is None or df.empty or len(df) < 5:
            return "NONE"

        # Clean multi-index headers if returned from yf
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 2. Extract Core Indicators via your system file module metrics
        df['atr'] = calculate_atr(df)
        dynamic_k = calculate_dynamic_k(df)
        power_direction, CEPower, PEPower = get_ce_pe_power(df)

        # 3. Synchronize Deep Historical Reference Vectors (Up to 4 candles back)
        for i in range(1, 5):
            df[f'open_p{i}'] = df['Open'].shift(i)
            df[f'high_p{i}'] = df['High'].shift(i)
            df[f'low_p{i}'] = df['Low'].shift(i)
            df[f'close_p{i}'] = df['Close'].shift(i)
        
        df['bar_range'] = df['High'] - df['Low']
        df['nr7_min'] = df['bar_range'].rolling(window=7).min()

        # Pre-compute candlestick characteristics
        body_size = (df['Close'] - df['Open']).abs()
        total_range = df['High'] - df['Low']
        safe_range = np.where(total_range == 0, 0.00001, total_range)
        upper_wick = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_wick = np.minimum(df['Open'], df['Close']) - df['Low']

        # 4. INITIALIZE ALL 13 ISOLATED STRATEGY PIPELINES
        pipelines = [
            'sig_degrad', 'sig_choch', 'sig_fvg', 'sig_ob', 'sig_quasimodo', 
            'sig_sweep', 'sig_sms', 'sig_marubozu', 'sig_engulfing', 
            'sig_inside', 'sig_nr7', 'sig_tsqueeze', 'sig_island'
        ]
        for pipe in pipelines:
            df[pipe] = "NONE"
            
        # Function continues smoothly into Part 2...



