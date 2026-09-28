# syssadxpxy.py
import numpy as np
import pandas as pd
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

def calculate_adx(df: pd.DataFrame) -> tuple:
    """
    Surgically computes pure directional indicator acceleration vectors.
    Allows BOTH CE and PE forces to grow simultaneously on volatile candles.
    
    Returns (ce_force, pe_force) mapped onto a dynamic range between 1.0 and 1.5.
    
    1.0 = Maximum Velocity/Growth (Premium expansion primed)
    1.5 = Absolute Stagnation/Contraction (Premium decay zone)
    """
    # 🎯 UPDATED: Baseline validation floor now requires minimum 43 rows to compute lookback depth
    if df is None or df.empty or len(df) < 43:
        return 1.5, 1.5

    high = df['High'].to_numpy()
    low = df['Low'].to_numpy()
    close = df['Close'].to_numpy()
    length = len(df)

    # 1. Allocate computational matrices for Directional Movement (DM) and True Range (TR)
    plus_dm = np.zeros(length)
    minus_dm = np.zeros(length)
    tr = np.zeros(length)

    # 2. Vectorized loop to calculate clean daily raw changes
    for i in range(1, length):
        tr[i] = max(
            high[i] - low[i], 
            abs(high[i] - close[i-1]), 
            abs(low[i] - close[i-1])
        )
        
        up_move = high[i] - high[i-1]
        down_move = low[i-1] - low[i]
        
        # 🔓 SIMULTANEOUS INDEPENDENT ACCUMULATION:
        # Both sides can grow on the same candle (e.g. wide outside candles)
        if up_move > 0:
            plus_dm[i] = up_move
            
        if down_move > 0:
            minus_dm[i] = down_move

    # 3. Apply standard rolling calculations for smoothed baseline trends
    # 🎯 UPDATED: Tracking lookback window shifted to a 42-candle architecture framework
    period = 42
    if length <= period:
        return 1.5, 1.5

    tr_sum = pd.Series(tr).rolling(window=period).sum().to_numpy()
    plus_dm_sum = pd.Series(plus_dm).rolling(window=period).sum().to_numpy()
    minus_dm_sum = pd.Series(minus_dm).rolling(window=period).sum().to_numpy()

    # Prevent ZeroDivision errors over flatline candles
    tr_sum = np.where(tr_sum == 0, 0.0001, tr_sum)

    # Derive raw directional indicators (+DI and -DI) over the 42-candle window
    di_plus = (plus_dm_sum / tr_sum) * 100
    di_minus = (minus_dm_sum / tr_sum) * 100

    # 4. 🎯 NORMALIZED SPECTRAL SPREAD CALCULATOR (1.0 TO 1.5 RANGE)
    curr_ce, prior_ce = di_plus[-1], di_plus[-2]
    curr_pe, prior_pe = di_minus[-1], di_minus[-2]

    def compute_scaled_force(current_val: float, prior_val: float, sensitivity: float = 0.20) -> float:
        if prior_val == 0:
            return 1.5
            
        # Calculate strict rate of change across sequential indicator values
        growth_rate = (current_val - prior_val) / prior_val
        
        # Immediate collapse to max decay if growth is flat or negative
        if growth_rate <= 0:
            return 1.5
            
        # Map the float sequence perfectly between 1.0 and 1.5 based on 20% sensitivity threshold
        scaled_val = 1.5 - (min(growth_rate / sensitivity, 1.0) * 0.5)
        return round(float(scaled_val), 2)

    # Generate isolated tracking values for Call (CE) and Put (PE) vectors
    ce_force = compute_scaled_force(curr_ce, prior_ce, sensitivity=0.20)
    pe_force = compute_scaled_force(curr_pe, prior_pe, sensitivity=0.20)

    return ce_force, pe_force
