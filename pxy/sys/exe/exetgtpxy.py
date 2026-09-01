def target_price(row):
    """Calculates individual option layer target price using dynamic volatility variables.

    Aligned Trades   : atr * atr (Minimum floor of 25.0, 4:1 dampened growth thereafter).
    Sideways Trades  : Strict ATR alone (Quick escape targeting to beat sideways Theta decay).
    Hostile Trades   : Fixed 1.4% target percentage floor.
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 2️⃣ INPUTS (SAFE) & PRE-CALCULATIONS
        atr = f(row.get("atr", 0))
        
        # Calculate volatility component once for the Aligned Strategy
        raw_vol = atr * atr
        vol_component = 25.0 if raw_vol <= 25.0 else 25.0 + ((raw_vol - 25.0) / 4.0)

        # 3️⃣ Context string extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()
        supertrend = str(row.get("supertrend", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 4️⃣ 3-Tier Target Profit Matrix Engine
        if is_ce:
            if supertrend == "SIDE":
                target_pct = atr / 1.4
            elif active_exit in ("SELL", "BEAR"):
                target_pct = 1.4
            else:
                target_pct = atr + vol_component

        elif is_pe:
            if supertrend == "SIDE":
                target_pct = atr / 1.4
            elif active_exit in ("BUY", "BULL"):
                target_pct = 1.4
            else:
                target_pct = atr + vol_component

        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0


