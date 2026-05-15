import pandas as pd 
from sysdtafpxy import fetch_yf_data 

USE_FORMING_CANDLE = True 
CANDLE_STYLE = "CLOSE" 

def get_close_data(tickerSymbol=None, df=None): 
    if df is None: 
        df = fetch_yf_data() 
    if df is None or df.empty: 
        return None, None, None, df 
        
    if not USE_FORMING_CANDLE: 
        df = df.iloc[:-1] 
        
    required_cols = ['Close'] 
    for col in required_cols: 
        if col not in df.columns: 
            return None, None, None, df 

    # ================================================== # 
    # 🔥 VALUE ASSIGNMENT (STRICTLY CLOSE PRICE)        # 
    # ================================================== # 
    close_output = df['Close'] 
    close_mirror = df['Close'] 
    
    # ================================================== # 
    # 🔥 COLOR LOGIC (CLOSE PRICE MOMENTUM)              # 
    # ================================================== # 
    trend_color = pd.Series(index=df.index, dtype='object') 
    
    for i in range(len(df)): 
        if pd.isna(df['Close'].iloc[i]): 
            trend_color.iloc[i] = "none" 
            continue 
        if i == 0: 
            trend_color.iloc[i] = "none" 
            continue 
            
        # 🔥 TREND DIRECTION DETERMINED STRICTLY BY CLOSE PRICE 
        if df['Close'].iloc[i] > df['Close'].iloc[i - 1]: 
            trend_color.iloc[i] = "green" 
        elif df['Close'].iloc[i] < df['Close'].iloc[i - 1]: 
            trend_color.iloc[i] = "red" 
        else: 
            trend_color.iloc[i] = trend_color.iloc[i - 1] 

    # ================================================== # 
    # 🔥 SIGNAL ENGINE (2 CANDLE HOLD + PATTERN LOGIC)   # 
    # ================================================== # 
    signal = pd.Series(index=df.index, dtype='object') 
    last_signal = None 
    hold_count = 0 
    
    for i in range(len(df)): 
        if i < 1: 
            signal.iloc[i] = "none" 
            continue 
            
        c0 = trend_color.iloc[i] 
        c1 = trend_color.iloc[i - 1] 
        c2 = trend_color.iloc[i - 2] if i >= 2 else None 
        new_signal = None 
        
        # ---------------- BUY LOGIC ---------------- 
        if c1 == "red" and c0 == "green": 
            new_signal = "BUY" 
        elif c2 == "red" and c1 == "green" and c0 == "green": 
            new_signal = "BUY" 
        elif c2 == "green" and c1 == "green" and c0 == "green": 
            new_signal = "BULL" 
            
        # ---------------- SELL LOGIC ---------------- 
        elif c1 == "green" and c0 == "red": 
            new_signal = "SELL" 
        elif c2 == "green" and c1 == "red" and c0 == "red": 
            new_signal = "SELL" 
        elif c2 == "red" and c1 == "red" and c0 == "red": 
            new_signal = "BEAR" 
            
        # ---------------- HOLD LOGIC ---------------- 
        if new_signal: 
            last_signal = new_signal 
            hold_count = 2 
            signal.iloc[i] = new_signal 
        elif hold_count > 0: 
            signal.iloc[i] = last_signal 
            hold_count -= 1 
        else: 
            signal.iloc[i] = "none" 

    # 👇 inject into df using a clean signal column name
    df["close_signal"] = signal 
    
    # Returns values in the exact original order positions
    return close_output, close_mirror, trend_color, df


