def target_price(row):
    """Calculates individual option layer target price based on exit conditions.

    Favorite Trade: (atr * atr) percentage target. Hostile Trade: 1.4% percentage target floor.
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0:
            return 0.0

        # 2️⃣ INPUTS (SAFE) & PRE-CALCULATIONS
        atr = f(row.get("atr", 0))

        # 3️⃣ Context string extractors
        symbol = str(row.get("symbol", "unknown")).upper()
        active_exit = str(row.get("exit", "NONE")).upper().strip()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        target_pct = 0.0

        # 4️⃣ Exit-Value Only Target Matrix
        if is_ce:
            # Hostile conditions for Calls
            if active_exit in ("SELL", "BEAR"):
                target_pct = 1.4
            else:
                target_pct = atr * atr

        elif is_pe:
            # Hostile conditions for Puts
            if active_exit in ("BUY", "BULL"):
                target_pct = 1.4
            else:
                target_pct = atr * atr

        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)

    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0

