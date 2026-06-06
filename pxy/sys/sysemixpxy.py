import pandas as pd
import numpy as np
import yfinance as yf
from colorama import Fore, Style, init

# Direct Module Imports from your local production directory
from syspowrpxy import get_ce_pe_power
from syskatrpxy import calculate_atr, calculate_dynamic_k

# Initialize terminal visual formats
init(autoreset=True)
TOTAL_WIDTH = 42

def generate_enterprise_pipeline_signals(ticker_symbol="^NSEI", period="5d"):
    """
    Downloads 1-minute high-frequency bars and executes 13 decentralized leading 
    price action pipelines. Consolidates them via an absolute priority selector.
    """
    print(f"{Fore.CYAN}📥 Spawning 13-Pipeline Decisive Matrix Engine for: {ticker_symbol}...")
    
    try:
        # 1. Download live 1-minute historical data layer safely from Yahoo Finance
        df = yf.download(tickers=ticker_symbol, period=period, interval="1m", progress=False)
        if df.empty:
            print(f"{Fore.RED}❌ Data Stream Error: Null dataframe from yf.")
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 2. Link and inject your Imported Production Math Metrics
        df['atr'] = calculate_atr(df)
        dynamic_k = calculate_dynamic_k(df)
        power_direction, CEPower, PEPower = get_ce_pe_power(df)

        # Broadcast telemetry metadata across tracking rows
        df['ce_power'] = CEPower
        df['pe_power'] = PEPower
        df['power_direction'] = power_direction
        df['k'] = dynamic_k

        # 3. Build Deep Historical Multibar Reference Vectors (Up to 4 candles back)
        for i in range(1, 5):
            df[f'open_p{i}'] = df['Open'].shift(i)
            df[f'high_p{i}'] = df['High'].shift(i)
            df[f'low_p{i}'] = df['Low'].shift(i)
            df[f'close_p{i}'] = df['Close'].shift(i)
        
        df['bar_range'] = df['High'] - df['Low']
        df['nr7_min'] = df['bar_range'].rolling(window=7).min()

        # Pre-compute candlestick structural characteristics
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
            
        # Code continues smoothly into Part 2...
