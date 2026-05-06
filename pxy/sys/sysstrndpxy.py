def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: Fixed Anchor + Smooth IST Merge Logic
    Fixed for Pandas 2.0+ and Python 3.12 compatibility.
    """
    df = df.copy()

    # 1. IST DATETIME FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
    
    # Ensure index is in IST
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC').tz_convert('Asia/Kolkata')
    else:
        df.index = df.index.tz_convert('Asia/Kolkata')

    # 2. Session Tracking
    df['date_only'] = df.index.date
    df['bar_count'] = df.groupby('date_only').cumcount() + 1

    # 3. Components: Session Price Mean & Dynamic 50 SMA
    session_mean = df.groupby('date_only')['Close'].expanding().mean().reset_index(level=0, drop=True)
    
    sma_50 = df.groupby('date_only')['Close'].apply(
        lambda x: x.expanding().mean() if len(x) <= 50 else x.rolling(window=50).mean()
    ).reset_index(level=0, drop=True)

    python_hybrid = (session_mean + sma_50) / 2

    # 4. FIXED ANCHOR LOGIC (Using transform to avoid ValueError)
    def get_first_bar_val(group):
        # Bullish 9:15 -> High, Bearish -> Low
        return group.iloc[0]['High'] if group.iloc[0]['Close'] > group.iloc[0]['Open'] else group.iloc[0]['Low']

    # transform broadcasts the single value to all rows in the group
    df['anchor'] = df.groupby('date_only', group_keys=False).apply(
        lambda x: pd.Series([get_first_bar_val(x)] * len(x), index=x.index),
        include_groups=False
    ).reset_index(level=0, drop=True)

    # 5. The No-Jump Black Line Logic (ST)
    blend_factor = (df['bar_count'] - 15) / 30.0
    
    df['ST'] = np.select(
        [
            df['bar_count'] <= 15,
            (df['bar_count'] > 15) & (df['bar_count'] <= 45)
        ],
        [
            df['anchor'],
            (df['anchor'] * (1 - blend_factor)) + (python_hybrid * blend_factor)
        ],
        default=python_hybrid
    )

    # 6. Signal Mapping
    st_trend = []
    prev_trend = "SIDE"
    for i in range(len(df)):
        curr_close = df['Close'].iloc[i]
        curr_line = df['ST'].iloc[i]
        
        if np.isnan(curr_line):
            st_trend.append("SIDE")
            continue
            
        if curr_close > curr_line:
            new_trend = "UP" if prev_trend in ["UP", "BUY"] else "BUY"
        elif curr_close < curr_line:
            new_trend = "DOWN" if prev_trend in ["DOWN", "SELL"] else "SELL"
        else:
            new_trend = "SIDE"
        
        st_trend.append(new_trend)
        prev_trend = new_trend
    
    df['ST_Trend'] = st_trend

    # Cleanup temporary columns to keep it clean
    df.drop(columns=['date_only', 'bar_count', 'anchor'], inplace=True)
    return df

