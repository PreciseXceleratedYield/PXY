import yfinance as yf
import pandas as pd
import numpy as np

def get_entry_signal():
    """
    Fetches NIFTY 50 data and returns the current Entry and Exit status.
    If no specific V5 signal (TB, TS, CB, CS) is found, the entry is synced
    to the exit status (BUY/BULL -> BULL, SELL/BEAR -> BEAR).
    """
    ticker_symbol = "^NSEI"
    
    try:
        df = yf.download(ticker_symbol, period='5d', interval='1m', progress=False)
        if df.empty or len(df) < 210:
            return "NONE", "NONE"
    except:
        return "NONE", "NONE"

    # ==========================================
    # 1. TREND & VOLATILITY CALCULATIONS
    # ==========================================
    df['sma200'] = df['Close'].rolling(window=200).mean()
    
    df['tr'] = pd.concat([
        (df['High'] - df['Low']),
        (df['High'] - df['Close'].shift(1)).abs(),
        (df['Low'] - df['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(window=14).mean()
    df['smoothed_atr'] = df['atr'].rolling(window=14).mean()

    df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    df['p_price'] = ((df['Close'] + (df['Close'] + df['Close'].shift(1))/2 +
                     (df['Close'] + df['Open'])/2 + df['ohlc4']) / 4).round(4)
    df['p_change'] = df['p_price'].diff()

    # ==========================================
    # 2. V2 TAXATION COUNTER ENGINE
    # ==========================================
    green_counts = np.zeros(len(df))
    red_counts = np.zeros(len(df))
    g, r = 0, 0

    for i in range(1, len(df)):
        change = df['p_change'].iloc[i]
        if change >= 0:
            g += 1
            if r == 1:
                r, g = 0, max(0, g - 2)
            elif r > 1: r = 0
        else:
            r += 1
            if g == 1:
                g, r = 0, max(0, r - 2)
            elif g > 1: g = 0
        green_counts[i], red_counts[i] = g, r

    df['gCount'], df['rCount'] = green_counts, red_counts

    # ==========================================
    # 3. EXIT LOGIC (Live Running Bar: -1)
    # ==========================================
    def get_layers(i):
        c, o, h, l = df['Close'].iloc[i], df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i]
        c1 = df['Close'].iloc[i-1]
        e1, e2 = c, (c1 + c) / 2
        e3, e4 = (c + o) / 2, (o + h + l + c) / 4
        p = round((e1 + e2 + e3 + e4) / 4, 4)
        return p, e1, e2, e3, e4

    p0, e1_0, e2_0, e3_0, e4_0 = get_layers(-1)
    p1, e1_1, e2_1, e3_1, e4_1 = get_layers(-2)
    p2, e1_2, e2_2, e3_2, e4_2 = get_layers(-3)

    r_l_pivot = (e1_0 > e1_1 and e1_2 > e1_1) or (e2_0 > e2_1 and e2_2 > e2_1) or \
                (e3_0 > e3_1 and e3_2 > e3_1) or (e4_0 > e4_1 and e4_2 > e4_1) or \
                (e1_0 < e1_1 and e1_2 < e1_1) or (e2_0 < e2_1 and e2_2 < e2_1) or \
                (e3_0 < e3_1 and e3_2 < e3_1) or (e4_0 < e4_1 and e4_2 < e4_1)

    if p0 > p1:
        exit_sig = "BUY" if r_l_pivot else "BULL"
    elif p0 < p1:
        exit_sig = "SELL" if r_l_pivot else "BEAR"
    else:
        exit_sig = "NONE"

    # ==========================================
    # 4. ENTRY LOGIC (Closed Bar: -2)
    # ==========================================
    idx = -2
    dyn_len = int(max(10, round(df['smoothed_atr'].iloc[idx])))
    atr_sma = df['Close'].iloc[idx - dyn_len + 1 : idx + 1].mean()
    
    isBull = atr_sma > df['sma200'].iloc[idx]
    isBear = atr_sma < df['sma200'].iloc[idx]
    
    flippedG = (df['p_change'].iloc[idx] >= 0) and (df['p_change'].iloc[idx-1] < 0)
    flippedR = (df['p_change'].iloc[idx] < 0) and (df['p_change'].iloc[idx-1] >= 0)
    
    pR, pG = df['rCount'].iloc[idx-1], df['gCount'].iloc[idx-1]
    
    entry = "NONE"
    if isBull and 3 <= pR < 7 and flippedG: entry = "TB"
    elif isBear and 3 <= pG < 7 and flippedR: entry = "TS"
    elif isBear and pR >= 7 and flippedG: entry = "CB"
    elif isBull and pG >= 7 and flippedR: entry = "CS"
    else:
        # Fallback Logic: Copy Exit status with required mapping
        if exit_sig in ["BUY", "BULL"]:
            entry = "BULL"
        elif exit_sig in ["SELL", "BEAR"]:
            entry = "BEAR"

    return entry, exit_sig

# --- CALLING THE FUNCTION ---
entry, exit = get_entry_signal()
print(f"Entry: {entry} | Exit: {exit}")
