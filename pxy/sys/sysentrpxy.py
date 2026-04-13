def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    debug_log("🕒 NOW:", now)

    # -------- PHASE 0: NONE --------
    if NONE_START <= now <= NONE_END:
        debug_log("⛔ NONE TIME WINDOW ACTIVE")
        return "NONE", "NONE"

    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")
        debug_log("📊 Fetched Data:", len(df) if df is not None else 0)

    if df is None or len(df) < 3:
        debug_log("❌ Insufficient Data")
        return "NONE", "NONE"

    # Ensure ST exists
    if 'ST' not in df.columns:
        debug_log("⚙️ Calculating Supertrend...")
        df = calculate_supertrend(df)

    last_st = df.iloc[-1]
    close = last_st['Close']
    st = last_st['ST'] if 'ST' in df.columns else close

    debug_log("📌 LAST CLOSE:", close, "ST:", st)

    # -------------------- BASE SIGNAL --------------------
    entry_signal, exit_signal = get_signal()
    debug_log("📡 RAW SIGNAL:", entry_signal, exit_signal)

    if entry_signal is None:
        entry_signal = "NONE"
        exit_signal = "NONE"

    # -------------------- ST MAPPING --------------------
    entry = map_entry(entry_signal, close, st, now)
    debug_log("🧠 AFTER ST MAP:", entry)

    # -------------------- ATR-SMA FILTER --------------------
    sma_data = get_atr_sma(df)
    sma_value = sma_data["atrsma"]
    debug_log("📉 ATR-SMA:", sma_value)

    last_sma = df.iloc[-2]
    close_sma = last_sma["Close"]

    entry = validate_with_sma(entry, close_sma, sma_value)
    debug_log("📊 AFTER SMA FILTER:", entry)

    # -------------------- BOS ENGINE --------------------
    bos_signal = get_bos(df)
    debug_log("🧩 BOS SIGNAL:", bos_signal)

    # CASE ENGINE
    if entry == "BULL" and bos_signal == "RBUY":
        entry = "OTMBUY"
    elif entry == "BEAR" and bos_signal == "RSELL":
        entry = "OTMSELL"
    elif entry == "NONE" and bos_signal == "RBUY":
        entry = "OTMBUY"
    elif entry == "NONE" and bos_signal == "RSELL":
        entry = "OTMSELL"

    debug_log("🏁 FINAL ENTRY:", entry)

    return entry, exit_signal
