import pandas as pd 
from sysdtafpxy import fetch_yf_data 

USE_FORMING_CANDLE = True 
CANDLE_STYLE = "HA" # Kept exactly the same to match configurations

def get_ha_data(tickerSymbol=None, df=None): 
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
    ha_close = df['Close'] 
    ha_open = df['Close'] 
    
    # ================================================== # 
    # 🔥 COLOR LOGIC (CLOSE PRICE MOMENTUM)              # 
    # ================================================== # 
    ha_color = pd.Series(index=df.index, dtype='object') 
    
    for i in range(len(df)): 
        if pd.isna(df['Close'].iloc[i]): 
            ha_color.iloc[i] = "none" 
            continue 
        if i == 0: 
            ha_color.iloc[i] = "none" 
            continue 
            
        # 🔥 TREND DIRECTION DETERMINED STRICTLY BY CLOSE PRICE 
        if df['Close'].iloc[i] > df['Close'].iloc[i - 1]: 
            ha_color.iloc[i] = "green" 
        elif df['Close'].iloc[i] < df['Close'].iloc[i - 1]: 
            ha_color.iloc[i] = "red" 
        else: 
            ha_color.iloc[i] = ha_color.iloc[i - 1] 

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
            
        c0 = ha_color.iloc[i] 
        c1 = ha_color.iloc[i - 1] 
        c2 = ha_color.iloc[i - 2] if i >= 2 else None 
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

    # 👇 Injected column name matches what sysdashpxy.py looks for
    df["ha_signal"] = signal 
    
    return ha_close, ha_open, ha_color, df

