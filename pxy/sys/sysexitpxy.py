def detect_raw_direction(df: pd.DataFrame) -> tuple:
    """
    Compares the running candle (C0) against the previous candle (C1).
    
    Returns:
        (latest_price, direction)
    
    Inter-Candle Structural Logic:
    - UP  : C0 Close > C1 Close
    - DOWN: C0 Close < C1 Close
    - NONE: C0 Close == C1 Close or missing data
    """
    # Ensure we have at least 2 candles to perform the comparison
    if df is None or len(df) < 2:
        return (None, "NONE")

    # Extract the last two rows
    c1_row = df.iloc[-2]  # Previous completed candle
    c0_row = df.iloc[-1]  # Current running candle

    # Assign close values
    c1_close = c1_row['Close']
    c0_close = c0_row['Close']  # This is the running price

    # Evaluate direction based on C1 vs C0
    if c0_close > c1_close:
        direction = "UP"
    elif c0_close < c1_close:
        direction = "DOWN"
    else:
        direction = "NONE"

    return (c0_close, direction)


