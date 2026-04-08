# ------------------------------
# SELF RUN (NO LOOP)
# ------------------------------
if __name__ == "__main__":
    df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 10:
        print("Not enough data")
        exit()

    # Apply HA
    df = apply_heikin_ashi(df)

    # Create debug columns
    df['ha_body'] = df['ha_close'] - df['ha_open']
    df['candle_body'] = df['Close'] - df['Open']

    # 🔥 Print last 10 candles (approx 10 minutes)
    debug_cols = [
        'Open', 'High', 'Low', 'Close',
        'ha_open', 'ha_close',
        'ha_body', 'candle_body'
    ]

    print("\n=== LAST 10 MIN DATA (DEBUG) ===")
    print(df[debug_cols].tail(10))

    # Signals
    entry_signal, exit_signal = get_signal()

    print("\n=== SIGNAL OUTPUT ===")
    print(f"ENTRY : {entry_signal}")
    print(f"EXIT  : {exit_signal}")
